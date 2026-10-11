"""Store POS exports (CSV).

v1 (legacy POS): one central file per business day, cp1252, '|', thousands separators ('1,299.99'),
    12-hour local time without offset ('03/14/2025 07:22:33 PM'), Windows line endings.
    No file when every store is closed.
v2 (new POS vendor): one file per store and day, UTF-8, ',', plain decimals, ISO-8601 with
    offset, renamed and reordered columns, tax_code letter -> tax_rate number (percent, depends on
    the store's state), new promo_code.
"""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from . import reference_data as ref
from .calendar_us import (STORE_HOURS_SUNDAY, STORE_HOURS_WEEKDAY, demand_multiplier, eastern_utc_offset,
                          is_black_week, is_trading_day, local_to_utc, next_trading_day, sample_local_time)
from .chaos import corrupt_amount, lateness, with_duplicates
from .formats import us_amount
from .rng import Weighted, make_rng, pick_weighted, poisson
from .world import CENT, ZERO, DayContext, Location, World, ean13, sales_tax_rate
from .writers import CsvFormat, OutputFile

V1_FORMAT = CsvFormat(
    columns=("store_code", "register_no", "receipt_no", "receipt_local_ts", "cashier_id", "line_no", "ean",
             "item_name", "quantity", "item_price", "item_discount", "tax_code", "transaction_type",
             "payment_type", "loyalty_card_no"),
    delimiter="|", encoding="cp1252", line_terminator="\r\n",
)
V2_FORMAT = CsvFormat(
    columns=("receipt_id", "store_code", "receipt_ts", "line_no", "ean", "item_name", "qty", "unit_price",
             "discount", "tax_rate", "tx_type", "payment_method", "loyalty_card_no", "promo_code", "cashier_id"),
    delimiter=",", encoding="utf-8", line_terminator="\n",
)
LATE_LOOKBACK_DAYS = 7  # covers two late export runs across store closure days
LINE_COUNTS = Weighted([(1, 0.6), (2, 0.25), (3, 0.1), (4, 0.04), (5, 0.01)])
PAYMENT_TYPES = Weighted([("CARD", 0.55), ("MOBILE_WALLET", 0.2), ("CASH", 0.17), ("INSTALLMENTS", 0.08)])
TRAINING_EAN = ean13("200000000000")  # in-store barcode range 20-29
STORE_DISCOUNT = Decimal("0.05")


@dataclass(frozen=True, slots=True)
class PosLine:
    store_code: str
    business_day: date
    register_no: int
    receipt_no: int
    local_ts: datetime  # naive America/New_York
    cashier_id: str
    line_no: int
    ean: str
    item_name: str
    quantity: int
    unit_price: Decimal
    discount: Decimal
    transaction_type: str  # SALE | RETURN | VOID
    payment_type: str
    loyalty_card_no: str | None
    receipt_index: int


def store_day_lines(world: World, store: Location, day: date) -> list[PosLine]:
    """All receipt lines of one store and business day. Pure function of (config, store, day)."""
    if not world.store_is_open(store, day):
        return []
    config = world.config
    context = world.day_context(day)
    if not context.store:
        return []
    rng = make_rng(config.seed, "pos", store.location_code, day)
    dirty_rng = make_rng(config.seed, "pos-dirty", store.location_code, day)  # dirt never shifts the facts
    expected = (config.receipts_per_store_per_day * config.scale * store.traffic_factor
                * demand_multiplier(day, "store") * _cannibalization(world, store, day))
    hours = STORE_HOURS_SUNDAY if day.weekday() == 6 else STORE_HOURS_WEEKDAY
    receipt_times = sorted(sample_local_time(rng, day, hours) for _ in range(poisson(rng, expected)))
    receipt_numbers: dict[int, int] = defaultdict(int)
    lines = []
    for receipt_index, local_ts in enumerate(receipt_times):
        register = rng.randint(1, store.registers)
        receipt_numbers[register] += 1
        cashier = rng.choice(store.cashiers)
        card = None
        if rng.random() < 0.4:
            holder = world.pick_card_holder(rng, local_to_utc(local_ts))
            card = holder.loyalty_card_no if holder else None
        unknown_card_roll, unknown_card_digits = dirty_rng.random(), dirty_rng.randrange(10**10)
        if card and unknown_card_roll < config.chaos.dirty_value_rate / 3:
            card = ean13(f"29{unknown_card_digits:010d}")  # a card number the CRM does not know
        if _is_training_receipt(rng, config.history_start, store, day):
            cashier = "TRAINING"  # test receipts from the opening week land in production data
            items = [(TRAINING_EAN, "TEST ITEM", 1, Decimal("1.00"), ZERO, "SALE")]
        else:
            items = _receipt_items(rng, context, cashier)
        total = sum((unit * quantity - discount for _, _, quantity, unit, discount, _ in items), ZERO)
        payment = PAYMENT_TYPES(rng)
        if payment == "INSTALLMENTS" and total < 250:
            payment = "CARD"
        for line_no, (ean, name, quantity, unit, discount, tx_type) in enumerate(items, start=1):
            unknown_ean_roll, unknown_ean_digits = dirty_rng.random(), dirty_rng.randrange(10**9)
            if unknown_ean_roll < config.chaos.dirty_value_rate / 30:
                ean = ean13(f"086{unknown_ean_digits:09d}")  # secondary barcode the ERP does not know
            lines.append(PosLine(store.location_code, day, register, receipt_numbers[register], local_ts, cashier,
                                 line_no, ean, name, quantity, unit, discount, tx_type, payment, card, receipt_index))
    return lines


def _cannibalization(world: World, store: Location, day: date) -> float:
    if store.location_code != ref.CANNIBALIZED_STORE:
        return 1.0
    return 0.82 if world.store_by_code[ref.NEW_NEIGHBOUR_STORE].is_open(day) else 1.0  # planted truth


def _is_training_receipt(rng: random.Random, history_start: date, store: Location, day: date) -> bool:
    opened_recently = store.opened_date >= history_start and day < store.opened_date + timedelta(days=3)
    return opened_recently and rng.random() < 0.05


def _receipt_items(rng: random.Random, context: DayContext, cashier: str) -> list[tuple]:
    if rng.random() < 0.025:  # return at the counter: negative quantity
        product = context.store[pick_weighted(rng, context.store_cum)]
        return [(product.ean, product.name, -1, context.price(product, "STORE"), ZERO, "RETURN")]
    void_rate = 0.12 if cashier == ref.FRAUD_CASHIER else 0.01  # planted truth
    items = []
    for _ in range(LINE_COUNTS(rng)):
        product = context.store[pick_weighted(rng, context.store_cum)]
        quantity = rng.choice((1, 1, 2)) if product.is_accessory else 1
        unit = context.price(product, "STORE")
        discount = ((unit * quantity * STORE_DISCOUNT).quantize(CENT, ROUND_HALF_UP)
                    if rng.random() < 0.04 else ZERO)
        items.append((product.ean, product.name, quantity, unit, discount, "SALE"))
        if rng.random() < void_rate:  # VOID cancels the line above: SUM(quantity) without a filter lies
            items.append((product.ean, product.name, -quantity, unit, discount, "VOID"))
    return items


def _arrival_day(business_day: date, delay: int) -> date:
    arrival = business_day
    for _ in range(delay):
        arrival = next_trading_day(arrival)
    return arrival


def pos_files(world: World, day: date, version: str) -> list[OutputFile]:
    config = world.config
    if day < config.history_start or not is_trading_day(day):
        return []
    batches = []
    for back in range(LATE_LOOKBACK_DAYS, -1, -1):
        business_day = day - timedelta(days=back)
        if business_day < config.history_start or not is_trading_day(business_day):
            continue
        for store in world.stores:
            if not world.store_is_open(store, business_day):
                continue
            delay = lateness(config, "pos", f"{store.location_code}#{business_day}")
            if _arrival_day(business_day, delay) == day:
                lines = store_day_lines(world, store, business_day)
                if lines:
                    batches.append((store.location_code, business_day, lines))
    batches.sort(key=lambda batch: batch[:2])
    if version == "v1":
        lines = [line for _, _, batch in batches for line in batch]
        if not lines:
            return []
        return [OutputFile("pos", "receipt_line", day, f"POS_EXPORT_{day:%Y%m%d}.csv", "csv",
                           _rows(world, lines, version, f"{day}"), csv_format=V1_FORMAT)]
    return [
        OutputFile("pos", "receipt_line", day, f"pos_{code}_{business_day:%Y%m%d}.csv", "csv",
                   _rows(world, batch, version, f"{code}#{business_day}"), csv_format=V2_FORMAT)
        for code, business_day, batch in batches
    ]


def _rows(world: World, lines: list[PosLine], version: str, file_key: str) -> list[list[str]]:
    config = world.config
    rate = config.chaos.type_corruption_rate
    corrupt_rng = make_rng(config.seed, "chaos-corrupt", "pos", file_key)
    quantity_col, price_col = (8, 9) if version == "v1" else (6, 7)
    rows = []
    for line in lines:
        row = _v1_row(line) if version == "v1" else _v2_row(world, line)
        if rate > 0:
            if corrupt_rng.random() < rate:
                row[price_col] = corrupt_amount(line.unit_price, corrupt_rng)
            if corrupt_rng.random() < rate:
                row[quantity_col] = f"{line.quantity} ea"
        rows.append(row)
    return with_duplicates(rows, config.chaos.duplicate_rate, make_rng(config.seed, "chaos-dup", "pos", file_key))


def _v1_row(line: PosLine) -> list[str]:
    return [
        line.store_code, str(line.register_no), f"{line.receipt_no:06d}",
        line.local_ts.strftime("%m/%d/%Y %I:%M:%S %p"), line.cashier_id, str(line.line_no), line.ean,
        line.item_name.upper()[:40], str(line.quantity), us_amount(line.unit_price),
        us_amount(line.discount) if line.discount else "", "T", line.transaction_type, line.payment_type,
        line.loyalty_card_no or "",
    ]


def _v2_row(world: World, line: PosLine) -> list[str]:
    offset_hours = int(eastern_utc_offset(local_to_utc(line.local_ts)).total_seconds() // 3600)
    tax_rate = sales_tax_rate(world.store_by_code[line.store_code].state) * 100
    return [
        f"{line.store_code}-{line.business_day:%Y%m%d}-{line.register_no}-{line.receipt_no:06d}",
        line.store_code, f"{line.local_ts:%Y-%m-%dT%H:%M:%S}{offset_hours:+03d}:00", str(line.line_no), line.ean,
        line.item_name[:60], str(line.quantity), f"{line.unit_price:.2f}", f"{line.discount:.2f}",
        f"{tax_rate.normalize():f}",
        line.transaction_type, line.payment_type, line.loyalty_card_no or "", _v2_promo_code(world, line),
        line.cashier_id,
    ]


def _v2_promo_code(world: World, line: PosLine) -> str:
    rng = make_rng(world.config.seed, "pos-v2-promo", line.store_code, line.business_day, line.receipt_index)
    if rng.random() >= 0.03:
        return ""
    return "BLACK-INSTORE" if is_black_week(line.business_day) else "NEWSLETTER10"
