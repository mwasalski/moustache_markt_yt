"""E-commerce order exports (JSON).

v1: one JSON array per day (an API dump - needs multiLine=true), ISO-8601 timestamps.
v2: JSON Lines (multiLine=true would now read only the first order!), epoch-millis timestamps,
    nested item price, new seller_id, channel MARKETPLACE renamed to ALLEGRO, fee_gross -> fee.
Each export is "changed since the last run": per UTC day, only the latest version of an order.
"""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from .calendar_pl import ONLINE_HOURS, demand_multiplier, is_black_week, local_to_utc, sample_local_time
from .chaos import corrupt_numbers, lateness, with_duplicates
from .formats import epoch_millis, iso_utc
from .rng import Weighted, make_rng, pick_weighted, poisson
from .world import CENT, CITY_PICKER, ZERO, Customer, DayContext, Location, Product, World
from .writers import OutputFile

LOOKBACK_DAYS = 30  # longest order lifecycle (payment, shipping, 14-day return) plus late delivery
MAX_DELAY_DAYS = 2
FREE_DELIVERY_FROM = Decimal("299.00")

CHANNELS = Weighted([("WEB", 0.62), ("APP", 0.28), ("MARKETPLACE", 0.10)])
LINE_COUNTS = Weighted([(1, 0.68), (2, 0.2), (3, 0.08), (4, 0.03), (5, 0.01)])
PAYMENTS = Weighted([("BLIK", 0.36), ("CARD", 0.24), ("TRANSFER", 0.12), ("INSTALLMENTS", 0.10),
                     ("PAY_LATER", 0.10), ("COD", 0.08)])
DELIVERIES = Weighted([("PARCEL_LOCKER", 0.52), ("COURIER", 0.30), ("STORE_PICKUP", 0.18)])
PROMO_RATES = (Decimal("0.05"), Decimal("0.10"), Decimal("0.15"))
GUEST_NAMES = ("kontakt", "zakupy", "gracz", "tomek", "kasia", "biuro", "ania", "marek")
GUEST_DOMAINS = ("gmail.com", "wp.pl", "onet.pl", "o2.pl", "interia.pl")
CORRUPTIBLE = {
    "v1": (("total_gross",), ("delivery", "fee_gross"), ("items", "*", "unit_price_gross"),
           ("items", "*", "discount_gross")),
    "v2": (("total_gross",), ("delivery", "fee"), ("items", "*", "price", "gross"),
           ("items", "*", "price", "discount")),
}


@dataclass(frozen=True, slots=True)
class OrderLine:
    line_no: int
    product: Product
    quantity: int
    unit_price: Decimal
    discount: Decimal
    extended_warranty: bool


@dataclass(frozen=True, slots=True)
class OrderVersion:
    at: datetime
    status: str
    payment_status: str
    paid_at: datetime | None


@dataclass(frozen=True, slots=True)
class Order:
    order_id: str
    channel: str
    customer: Customer | None
    guest_email: str | None
    is_b2b: bool
    created_at: datetime
    voucher_code: str | None
    payment_method: str
    delivery_method: str
    pickup_location_id: int | None
    delivery_postal_code: str
    delivery_city: str
    fee: Decimal
    total: Decimal  # header total: may differ from SUM(lines) by a cent (discount allocation)
    lines: tuple[OrderLine, ...]
    versions: tuple[OrderVersion, ...]

    def export_versions(self) -> dict[date, int]:
        """UTC day -> index of the last version that day (what a daily 'changed since' export sees)."""
        latest: dict[date, int] = {}
        for index, version in enumerate(self.versions):
            latest[version.at.date()] = index
        return latest


# --------------------------------------------------------------------------- generation


def generate_orders(world: World, created_day: date) -> list[Order]:
    """All orders placed on a local (Europe/Warsaw) day. Pure function of (config, day)."""
    config = world.config
    context = world.day_context(created_day)
    if not context.online:
        return []
    rng = make_rng(config.seed, "ecom", created_day)
    count = poisson(rng, config.online_orders_per_day * config.scale * demand_multiplier(created_day, "online"))
    sequence: dict[str, int] = defaultdict(int)
    return [_order(world, context, rng, created_day, sequence) for _ in range(count)]


def _order(world: World, context: DayContext, rng: random.Random, day: date, sequence: dict[str, int]) -> Order:
    channel = CHANNELS(rng)
    created_at = local_to_utc(sample_local_time(rng, day, ONLINE_HOURS))
    if channel == "MARKETPLACE":
        order_id = f"ALG-{rng.getrandbits(40):010x}"
    else:
        sequence[channel] += 1
        order_id = f"{channel}-{day:%y%m%d}-{sequence[channel]:05d}"

    customer, guest_email = None, None
    if channel == "MARKETPLACE":
        guest_email = f"{rng.getrandbits(48):012x}@allegromail.pl"  # marketplaces mask buyer e-mails
    elif channel == "WEB" and rng.random() < 0.25:
        guest_email = _guest_email(rng)
    else:
        customer = world.pick_customer(rng, created_at)
        if customer is None:
            guest_email = _guest_email(rng)
    is_b2b = (customer.customer_type == "B2B") if customer else rng.random() < 0.03

    drafts = _draft_lines(rng, context)
    subtotal = sum((unit * quantity - promo for _, quantity, unit, promo, _ in drafts), ZERO)
    voucher_code, header_discount = _voucher(rng, day, channel, subtotal)
    lines = tuple(
        OrderLine(line_no, product, quantity, unit,
                  promo + _allocate(header_discount, unit * quantity - promo, subtotal), warranty)
        for line_no, (product, quantity, unit, promo, warranty) in enumerate(drafts, start=1)
    )

    payment = PAYMENTS(rng)
    if payment == "INSTALLMENTS" and subtotal < 500:
        payment = "BLIK"
    if payment == "PAY_LATER" and subtotal > 4000:
        payment = "CARD"
    delivery = "COURIER" if payment == "COD" else DELIVERIES(rng)
    pickup_location_id = None
    if delivery == "STORE_PICKUP":
        store = _pickup_store(world, rng, customer, day)
        if store is None:
            delivery = "PARCEL_LOCKER"
        else:
            pickup_location_id = store.location_id
    if customer is not None:
        city, postal_code = customer.city, customer.postal_code
    else:
        city_spec = CITY_PICKER(rng)
        city, postal_code = city_spec.name, f"{city_spec.postal_prefix}-{rng.randrange(1000):03d}"
    fee = _delivery_fee(delivery, payment, subtotal - header_discount)
    return_factor = sum(line.product.return_factor for line in lines) / len(lines)
    versions = _lifecycle(rng, created_at, payment, delivery, return_factor)
    return Order(order_id, channel, customer, guest_email, is_b2b, created_at, voucher_code, payment, delivery,
                 pickup_location_id, postal_code, city, fee, subtotal - header_discount + fee, lines, versions)


def _draft_lines(rng: random.Random, context: DayContext) -> list[tuple[Product, int, Decimal, Decimal, bool]]:
    drafts, seen = [], set()
    for position in range(LINE_COUNTS(rng)):
        use_accessory = position > 0 and bool(context.accessories) and rng.random() < 0.55
        pool, cum = (context.accessories, context.accessory_cum) if use_accessory else (context.online, context.online_cum)
        product = pool[pick_weighted(rng, cum)]
        if product.product_id in seen:
            continue
        seen.add(product.product_id)
        quantity = rng.choice((1, 1, 1, 2, 3)) if product.is_accessory else (2 if rng.random() < 0.04 else 1)
        unit = context.price(product, "ONLINE")
        promo = ((unit * quantity * rng.choice(PROMO_RATES)).quantize(CENT, ROUND_HALF_UP)
                 if rng.random() < 0.06 else ZERO)
        warranty = unit >= 1000 and rng.random() < 0.12
        drafts.append((product, quantity, unit, promo, warranty))
    return drafts


def _allocate(header_discount: Decimal, line_net: Decimal, subtotal: Decimal) -> Decimal:
    """Header voucher spread over lines; per-line rounding is why header and lines may not reconcile."""
    if header_discount == ZERO or subtotal == ZERO:
        return ZERO
    return (header_discount * line_net / subtotal).quantize(CENT, ROUND_HALF_UP)


def _voucher(rng: random.Random, day: date, channel: str, subtotal: Decimal) -> tuple[str | None, Decimal]:
    if rng.random() >= 0.08:
        return None, ZERO
    if is_black_week(day):
        return "BLACK15", (subtotal * Decimal("0.15")).quantize(CENT, ROUND_HALF_UP)
    if day.month == 12 and subtotal >= 500:
        return "XMAS50", Decimal("50.00")
    if channel == "APP":
        return "APKA5", (subtotal * Decimal("0.05")).quantize(CENT, ROUND_HALF_UP)
    return "WITAJ10", (subtotal * Decimal("0.10")).quantize(CENT, ROUND_HALF_UP)


def _pickup_store(world: World, rng: random.Random, customer: Customer | None, day: date) -> Location | None:
    open_stores = [store for store in world.stores if store.is_open(day)]
    if not open_stores:
        return None
    if customer is not None:
        local = [store for store in open_stores if store.city == customer.city]
        if local and rng.random() < 0.7:
            return rng.choice(local)
    return rng.choice(open_stores)


def _delivery_fee(delivery: str, payment: str, amount: Decimal) -> Decimal:
    if delivery == "STORE_PICKUP":
        return ZERO
    base = ZERO if amount >= FREE_DELIVERY_FROM else (Decimal("9.99") if delivery == "PARCEL_LOCKER" else Decimal("15.99"))
    return base + (Decimal("5.00") if payment == "COD" else ZERO)


def _guest_email(rng: random.Random) -> str:
    return f"{rng.choice(GUEST_NAMES)}{rng.randint(1, 9999)}@{rng.choice(GUEST_DOMAINS)}"


def _lifecycle(rng: random.Random, created_at: datetime, payment: str, delivery: str,
               return_factor: float) -> tuple[OrderVersion, ...]:
    def minutes(low: float, high: float) -> timedelta:
        return timedelta(minutes=rng.uniform(low, high))

    def hours(low: float, high: float) -> timedelta:
        return timedelta(hours=rng.uniform(low, high))

    versions = [OrderVersion(created_at, "CREATED", "PENDING", None)]
    failure_roll = rng.random()
    if payment in ("BLIK", "CARD"):
        failed, pay_delay, cancel_delay = failure_roll < 0.03, minutes(1, 12), minutes(5, 30)
    elif payment == "TRANSFER":  # unpaid transfers are cancelled after three days
        failed, pay_delay, cancel_delay = failure_roll < 0.12, hours(1, 48), hours(72, 75)
    elif payment == "INSTALLMENTS":  # credit decision
        failed, pay_delay, cancel_delay = failure_roll < 0.15, hours(1, 20), hours(2, 24)
    elif payment == "PAY_LATER":
        failed, pay_delay, cancel_delay = failure_roll < 0.06, minutes(1, 5), minutes(5, 30)
    else:  # COD: the courier collects the money
        failed, pay_delay, cancel_delay = False, None, None
    if failed:
        versions.append(OrderVersion(created_at + cancel_delay, "CANCELLED", "FAILED", None))
        return tuple(versions)

    paid_at = created_at + pay_delay if pay_delay is not None else None
    if paid_at is not None:
        versions.append(OrderVersion(paid_at, "PAID", "PAID", paid_at))
    ready_at = paid_at or created_at
    if rng.random() < 0.02:  # customer cancels before shipping
        refund_status = "REFUNDED" if paid_at else "CANCELLED"
        versions.append(OrderVersion(ready_at + hours(1, 10), "CANCELLED", refund_status, paid_at))
        return tuple(versions)

    shipped_at = ready_at + hours(2, 30)
    versions.append(OrderVersion(shipped_at, "SHIPPED", "PAID" if paid_at else "PENDING", paid_at))
    delivered_at = shipped_at + hours(18, 72) + (hours(0, 72) if delivery == "STORE_PICKUP" else timedelta())
    paid_at = paid_at or delivered_at
    versions.append(OrderVersion(delivered_at, "DELIVERED", "PAID", paid_at))
    return_probability = 0.045 * return_factor * (2.0 if payment == "PAY_LATER" else 1.0)  # planted truth
    if rng.random() < return_probability:
        returned_at = delivered_at + timedelta(days=rng.uniform(1, 14))
        versions.append(OrderVersion(returned_at, "RETURNED", "REFUNDED", paid_at))
    return tuple(versions)


class OrderCache:
    """Orders by creation day. A backfill reuses them; a daily run regenerates the lookback window."""

    def __init__(self, world: World) -> None:
        self._world = world
        self._orders: dict[date, list[Order]] = {}

    def orders_created_on(self, day: date) -> list[Order]:
        if day not in self._orders:
            self._orders[day] = generate_orders(self._world, day)
        return self._orders[day]

    def evict_before(self, day: date) -> None:
        for cached_day in [d for d in self._orders if d < day]:
            del self._orders[cached_day]


# --------------------------------------------------------------------------- export


def ecom_files(world: World, day: date, version: str, cache: OrderCache) -> list[OutputFile]:
    config = world.config
    first_export_day = max(day - timedelta(days=MAX_DELAY_DAYS), config.history_start)
    picked = []
    # local day + 1 is included: an order placed at 00:30 in Warsaw happened "yesterday" in UTC
    for offset in range(-LOOKBACK_DAYS, 2):
        for order in cache.orders_created_on(day + timedelta(days=offset)):
            for export_day, index in order.export_versions().items():
                if not first_export_day <= export_day <= day:
                    continue
                delay = lateness(config, "ecom", f"{order.order_id}#{index}")
                if export_day + timedelta(days=delay) == day:
                    picked.append((delay > 0, order.versions[index].at, order.order_id, order, index))
    picked.sort(key=lambda item: item[:3])  # on time first (by time), late records at the end
    records = [_serialize(world, order, index, version) for *_, order, index in picked]

    if config.chaos.type_corruption_rate > 0:
        corrupt_rng = make_rng(config.seed, "chaos-corrupt", "ecom", day)
        for record in records:
            corrupt_numbers(record, CORRUPTIBLE[version], config.chaos.type_corruption_rate, corrupt_rng)
    records = with_duplicates(records, config.chaos.duplicate_rate, make_rng(config.seed, "chaos-dup", "ecom", day))
    fmt, extension = ("json_array", "json") if version == "v1" else ("jsonl", "jsonl")
    return [OutputFile("ecom", "orders", day, f"orders_{day:%Y%m%d}.{extension}", fmt, records)]


def _serialize(world: World, order: Order, index: int, version: str) -> dict:
    current = order.versions[index]
    v2 = version == "v2"
    stamp = epoch_millis if v2 else iso_utc
    return {
        "order_id": order.order_id,
        "channel": "ALLEGRO" if v2 and order.channel == "MARKETPLACE" else order.channel,
        "customer_id": order.customer.customer_id if order.customer else None,
        "guest_email": order.guest_email,
        "is_b2b": order.is_b2b,
        "order_status": current.status,
        "created_at": stamp(order.created_at),
        "updated_at": stamp(current.at),
        "currency_code": "PLN",
        "total_gross": order.total,
        "voucher_code": order.voucher_code,
        "payment": {
            "method": order.payment_method,
            "status": current.payment_status,
            "paid_at": stamp(current.paid_at) if current.paid_at else None,
        },
        "delivery": {
            "method": order.delivery_method,
            "pickup_location_id": order.pickup_location_id,
            "postal_code": order.delivery_postal_code,
            "city": order.delivery_city,
            ("fee" if v2 else "fee_gross"): order.fee,
        },
        "items": [_serialize_line(world, order, line, v2) for line in order.lines],
    }


def _serialize_line(world: World, order: Order, line: OrderLine, v2: bool) -> dict:
    if not v2:
        return {
            "line_no": line.line_no, "sku": line.product.sku, "quantity": line.quantity,
            "unit_price_gross": line.unit_price, "discount_gross": line.discount,
            "extended_warranty": line.extended_warranty,
        }
    rng = make_rng(world.config.seed, "ecom-v2-seller", order.order_id, line.line_no)
    roll, seller_number = rng.random(), rng.randrange(10_000, 100_000)
    return {
        "line_no": line.line_no, "sku": line.product.sku, "quantity": line.quantity,
        "price": {"gross": line.unit_price, "discount": line.discount},
        "extended_warranty": line.extended_warranty,
        "seller_id": f"S-{seller_number}" if roll < 0.07 else None,  # marketplace launch: 3rd-party sellers
    }
