"""The simulated world: master data and customer timelines.

The world is a pure function of the config, and every daily file is a projection of it.
That is why any single day can be regenerated without generating the days before it.
"""

from __future__ import annotations

import random
from bisect import bisect_left
from collections import OrderedDict, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from itertools import accumulate

from . import reference_data as ref
from .calendar_pl import ONLINE_HOURS, demand_multiplier, is_black_week, is_trading_day, local_to_utc, sample_local_time
from .config import SimulationConfig
from .formats import UTC
from .rng import Weighted, make_rng, pick_weighted, poisson, uuid_from

CENT = Decimal("0.01")
ZERO = Decimal("0.00")
VAT_RATE = Decimal("0.23")
DAY_CONTEXT_CACHE_SIZE = 48
APP_LAUNCH = date(2019, 3, 1)
CUSTOMERS_SINCE = datetime(2016, 1, 1, tzinfo=UTC)
CATEGORIES_CREATED_AT = datetime(2019, 1, 7, 8, 0, tzinfo=UTC)

CITY_PICKER = Weighted([(city, city.weight) for city in ref.CITIES])
EMAIL_DOMAIN_PICKER = Weighted(ref.EMAIL_DOMAINS)
REGISTRATION_CHANNELS = Weighted([("WEB", 0.6), ("APP", 0.25), ("STORE", 0.15)])
PHONE_STYLES = Weighted([(1, 0.4), (0, 0.3), (2, 0.15), (4, 0.1), (3, 0.05)])
CHANGE_KINDS = Weighted([("EMAIL", 0.25), ("PHONE", 0.15), ("ADDRESS", 0.15), ("CONSENT", 0.25), ("LOYALTY", 0.2)])
ENERGY_CLASSES = ("C", "D", "E", "E", "F", "F", "G")
TRANSLITERATION = str.maketrans("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ", "acelnoszzACELNOSZZ")
PII_FIELDS = ("first_name", "last_name", "company_name", "tax_id", "email", "phone_digits", "birth_date",
              "postal_code", "loyalty_card_no")


def at_utc(day: date, hour: int = 6) -> datetime:
    return datetime.combine(day, time(hour), tzinfo=UTC)


def money(value: float | Decimal) -> Decimal:
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def retail_round(value: float) -> Decimal:
    """Polish shelf prices: 1 299,99 / 49,99."""
    if value >= 100:
        return Decimal(int(value // 10) * 10) - CENT
    if value >= 10:
        return Decimal(int(value)) - CENT
    return Decimal(f"{max(value, 0.99):.2f}")


def ean13(first12: str) -> str:
    total = sum(int(digit) * (3 if position % 2 else 1) for position, digit in enumerate(first12))
    return first12 + str((10 - total % 10) % 10)


NIP_WEIGHTS = (6, 5, 7, 2, 3, 4, 5, 6, 7)


def is_valid_nip(nip: str) -> bool:
    if len(nip) != 10 or not nip.isdigit():
        return False
    check = sum(int(d) * w for d, w in zip(nip, NIP_WEIGHTS)) % 11
    return check == int(nip[-1])


def _nip(rng: random.Random) -> str:
    while True:
        digits = [rng.randint(1, 9)] + [rng.randrange(10) for _ in range(8)]
        check = sum(d * w for d, w in zip(digits, NIP_WEIGHTS)) % 11
        if check < 10:
            return "".join(map(str, digits)) + str(check)


def loyalty_card_number(customer_index: int) -> str:
    """Unique per customer: an affine map that is a bijection modulo 10**10."""
    return ean13("29" + f"{(customer_index * 7_919_993 + 13) % 10**10:010d}")


# --------------------------------------------------------------------------- categories


@dataclass(frozen=True, slots=True)
class Category:
    category_id: int
    parent_category_id: int | None
    category_code: str
    category_level: int
    original_name: str
    renamed_on: date | None = None
    new_name: str | None = None

    def name_on(self, day: date) -> str:
        return self.new_name if self.renamed_on and day >= self.renamed_on else self.original_name

    def updated_at_on(self, day: date) -> datetime:
        return at_utc(self.renamed_on) if self.renamed_on and day >= self.renamed_on else CATEGORIES_CREATED_AT


def build_categories() -> list[Category]:
    categories: list[Category] = []
    ids = iter(range(100, 1000))

    def add(code: str, name: str, level: int, parent: int | None) -> int:
        renamed_on, new_name = ref.CATEGORY_RENAMES.get(code, (None, None))
        categories.append(Category(next(ids), parent, code, level, name, renamed_on, new_name))
        return categories[-1].category_id

    for root_code, root_name, children in ref.CATEGORY_TREE:
        root_id = add(root_code, root_name, 1, None)
        for mid_code, mid_name, leaf_codes in children:
            mid_id = add(mid_code, mid_name, 2, root_id)
            for leaf_code in leaf_codes:
                add(leaf_code, ref.LEAVES[leaf_code].name, 3, mid_id)
    return categories


# --------------------------------------------------------------------------- products


@dataclass(frozen=True, slots=True)
class Product:
    product_id: int
    sku: str
    ean: str
    name: str
    brand_name: str  # as typed into the ERP - sometimes a dirty variant
    leaf_code: str
    category_id: int
    base_price: float  # gross PLN at launch
    cost_ratio: float  # net cost / net price
    weight_kg: Decimal
    warranty_months: int
    energy_class: str | None
    launch_date: date
    eol_date: date | None
    popularity: float
    in_store_assortment: bool
    is_accessory: bool
    return_factor: float
    promo_years: frozenset[int]

    @property
    def created_at(self) -> datetime:
        return at_utc(self.launch_date - timedelta(days=30), 9)

    def status_on(self, day: date) -> tuple[str, datetime]:
        if day < self.launch_date:
            return "DRAFT", self.created_at
        if self.eol_date is None or day < self.eol_date:
            return "ACTIVE", at_utc(self.launch_date)
        if day < self.eol_date + timedelta(days=90):
            return "EOL", at_utc(self.eol_date)
        return "DISCONTINUED", at_utc(self.eol_date + timedelta(days=90))

    def is_sellable(self, day: date) -> bool:
        return self.launch_date <= day and (self.eol_date is None or day < self.eol_date + timedelta(days=90))

    def _age_factor(self, day: date) -> float:
        months = max(0.0, (day - self.launch_date).days / 30.44)
        return max(0.62, 1.0 - 0.011 * months)

    def price_on(self, day: date, channel: str) -> Decimal:
        price = self.base_price * self._age_factor(day)
        if day.year in self.promo_years and is_black_week(day):
            price *= 0.85
        if self.eol_date is not None and day >= self.eol_date:
            price *= 0.85  # clearance
        if channel == "STORE" and self.product_id % 20 == 0:
            price *= 1.03  # a few SKUs cost more in stores than online
        return retail_round(price)

    def standard_cost_on(self, day: date) -> Decimal | None:
        if day < self.launch_date:
            return None
        month_start = max(day.replace(day=1), self.launch_date)
        return money(self.base_price * self._age_factor(month_start) / 1.23 * self.cost_ratio)

    def cost_changed_at(self, day: date) -> datetime:
        month_start = day.replace(day=1)
        return at_utc(month_start, 2) if month_start > self.launch_date else at_utc(self.launch_date)


def _launch_date(rng: random.Random) -> date:
    if rng.random() < 0.55:
        start, end = date(2022, 1, 1), date(2024, 12, 31)
    else:
        start, end = date(2025, 1, 1), date(2027, 6, 30)
    return start + timedelta(days=rng.randint(0, (end - start).days))


def _unique_ean(rng: random.Random, brand: str, used: set[str]) -> str:
    prefix = ref.EAN_PREFIXES.get(brand, "590")
    while True:
        ean = ean13(prefix + "".join(str(rng.randrange(10)) for _ in range(12 - len(prefix))))
        if ean not in used:
            used.add(ean)
            return ean


def _erp_brand_name(config: SimulationConfig, index: int, brand: str) -> str:
    rng = make_rng(config.seed, "product-dirty", index)
    roll, variant_pick = rng.random(), rng.random()  # always two draws: chaos rates never shift other data
    variants = ref.BRAND_VARIANTS.get(brand)
    if variants and roll < config.chaos.dirty_value_rate * 2:
        return variants[int(variant_pick * len(variants))]
    return brand


def build_products(config: SimulationConfig, categories: list[Category]) -> list[Product]:
    leaf_ids = {c.category_code: c.category_id for c in categories if c.category_level == 3}
    leaves = Weighted([(leaf, leaf.share) for leaf in ref.LEAVES.values()])
    ranks = list(range(1, config.products + 1))
    make_rng(config.seed, "product-ranks").shuffle(ranks)
    used_eans: set[str] = set()
    products = []
    for index in range(config.products):
        rng = make_rng(config.seed, "product", index)
        leaf = leaves(rng)
        brand, models = rng.choice(leaf.models)
        name = f"{leaf.product_type} {brand} {rng.choice(models)} {rng.choice(leaf.specs)}"
        launch = _launch_date(rng)
        eol = launch + timedelta(days=rng.randint(540, 1460))
        products.append(Product(
            product_id=10_000 + index,
            sku=f"SK-{(index * 7919 + 104_729) % 1_000_000:06d}",
            ean=_unique_ean(rng, brand, used_eans),
            name=name,
            brand_name=_erp_brand_name(config, index, brand),
            leaf_code=leaf.code,
            category_id=leaf_ids[leaf.code],
            base_price=leaf.median_price * rng.lognormvariate(0, 0.25),
            cost_ratio=rng.uniform(0.72, 0.9),
            weight_kg=Decimal(f"{rng.uniform(*leaf.weight_kg):.3f}"),
            warranty_months=leaf.warranty_months,
            energy_class=rng.choice(ENERGY_CLASSES) if leaf.energy_label else None,
            launch_date=launch,
            eol_date=eol if eol <= config.world_end else None,
            popularity=(1.0 / ranks[index] ** 1.05) * (1000.0 / (leaf.median_price + 300.0)) ** 0.5,
            in_store_assortment=rng.random() < leaf.store_share,
            is_accessory=leaf.median_price < 300,
            return_factor=leaf.return_factor,
            promo_years=frozenset(year for year in range(2022, 2028) if rng.random() < 0.3),
        ))
    return products


# --------------------------------------------------------------------------- locations


@dataclass(frozen=True, slots=True)
class Location:
    location_id: int
    location_code: str
    location_name: str
    location_type: str  # STORE | DC | ONLINE
    store_format: str | None
    city: str | None
    voivodeship: str | None
    postal_code: str | None
    latitude: Decimal | None
    longitude: Decimal | None
    floor_area_m2: int | None
    opened_date: date
    closed_date: date | None
    registers: int = 0
    traffic_factor: float = 0.0
    cashiers: tuple[str, ...] = ()

    @property
    def created_at(self) -> datetime:
        return at_utc(self.opened_date - timedelta(days=60), 8)

    def is_open(self, day: date) -> bool:
        return self.opened_date <= day and (self.closed_date is None or day < self.closed_date)


_REGISTERS = {"FLAGSHIP": 6, "STANDARD": 4, "OUTLET": 3}
_FLOOR_AREA = {"FLAGSHIP": (1200, 1800), "STANDARD": (400, 800), "OUTLET": (550, 650)}
_TRAFFIC = {"FLAGSHIP": 1.6, "STANDARD": 1.0, "OUTLET": 0.7}


def build_locations(config: SimulationConfig) -> list[Location]:
    cities = {city.name: city for city in ref.CITIES}
    locations = []
    for location_id, spec in enumerate(ref.STORES, start=1):
        rng = make_rng(config.seed, "location", spec.code)
        city = cities[spec.city]
        registers = _REGISTERS[spec.store_format]
        cashiers = {f"K{rng.randrange(1000, 10_000)}" for _ in range(registers * 2 + 2)}
        if spec.code == ref.FRAUD_STORE:
            cashiers.add(ref.FRAUD_CASHIER)
        locations.append(Location(
            location_id, spec.code, spec.name, "STORE", spec.store_format, city.name, city.voivodeship,
            f"{city.postal_prefix}-{rng.randrange(1000):03d}",
            Decimal(f"{city.latitude + rng.uniform(-0.03, 0.03):.6f}"),
            Decimal(f"{city.longitude + rng.uniform(-0.03, 0.03):.6f}"),
            rng.randint(*_FLOOR_AREA[spec.store_format]), spec.opened, spec.closed, registers,
            _TRAFFIC[spec.store_format] * (1.15 if city.weight > 0.75 else 1.0), tuple(sorted(cashiers)),
        ))
    for location_id, site in enumerate(ref.DISTRIBUTION_CENTERS, start=len(ref.STORES) + 1):
        locations.append(Location(
            location_id, site.code, site.name, "DC", None, site.city, site.voivodeship, site.postal_code,
            Decimal(f"{site.latitude:.6f}"), Decimal(f"{site.longitude:.6f}"), None, site.opened, None,
        ))
    locations.append(Location(ref.ONLINE_LOCATION_ID, "ONLINE", "Sklep internetowy", "ONLINE",
                              None, None, None, None, None, None, None, date(2014, 1, 1), None))
    return locations


# --------------------------------------------------------------------------- customers


@dataclass(frozen=True, slots=True)
class CustomerChange:
    at: datetime
    kind: str  # EMAIL | PHONE | ADDRESS | CONSENT | LOYALTY | ERASE | DELETE


@dataclass(frozen=True, slots=True)
class Customer:
    index: int
    customer_id: str
    customer_type: str  # B2C | B2B
    first_name: str
    last_name: str
    company_name: str | None
    tax_id: str | None
    email: str
    phone_digits: str
    phone_style: int
    birth_date: date | None
    city: str
    postal_code: str
    registration_channel: str
    registered_at: datetime
    loyalty_card_no: str | None
    loyalty_tier: str
    marketing_consent: bool
    weight: float  # Pareto-distributed purchase propensity
    changes: tuple[CustomerChange, ...]
    end_at: datetime | None  # erasure (GDPR) or account deletion: no activity afterwards


def make_email(rng: random.Random, first: str, last: str, dirty_rate: float) -> str:
    first_ascii, last_ascii = first.translate(TRANSLITERATION).lower(), last.translate(TRANSLITERATION).lower()
    pattern, number, domain = rng.randrange(4), rng.randint(1, 99), EMAIL_DOMAIN_PICKER(rng)
    local = (f"{first_ascii}.{last_ascii}", f"{first_ascii}{last_ascii}{number}",
             f"{first_ascii[0]}{last_ascii}", f"{last_ascii}.{first_ascii}{number}")[pattern]
    email = f"{local}@{domain}"
    roll, style = rng.random(), rng.randrange(4)
    if roll < dirty_rate:
        email = (email.upper(), f" {email}", f"{email} ", email.capitalize())[style]
    return email


def random_phone(rng: random.Random) -> str:
    return rng.choice("5678") + "".join(str(rng.randrange(10)) for _ in range(8))


def _registration_moments(config: SimulationConfig) -> list[datetime]:
    rng = make_rng(config.seed, "customers-initial")
    go_live = at_utc(config.history_start, 0)
    span = (go_live - CUSTOMERS_SINCE).total_seconds()
    initial_count = round(config.initial_customers * config.scale)
    moments = [CUSTOMERS_SINCE + timedelta(seconds=span * rng.random() ** 0.6) for _ in range(initial_count)]
    day = config.history_start
    while day <= config.world_end:
        day_rng = make_rng(config.seed, "customers-new", day)
        expected = config.new_customers_per_day * config.scale * demand_multiplier(day, "online") ** 0.5
        count = poisson(day_rng, expected)
        moments.extend(local_to_utc(sample_local_time(day_rng, day, ONLINE_HOURS)) for _ in range(count))
        day += timedelta(days=1)
    return sorted(moments)


def _timeline(rng: random.Random, registered_at: datetime, config: SimulationConfig):
    horizon = datetime.combine(config.world_end, time(23, 59, 59), tzinfo=UTC)
    exit_roll, exit_point = rng.random(), rng.random()
    end_at, end_kind = None, None
    earliest_exit = registered_at + timedelta(days=30)
    if exit_roll < 0.0065 and earliest_exit < horizon:
        end_kind = "ERASE" if exit_roll < 0.004 else "DELETE"
        end_at = earliest_exit + (horizon - earliest_exit) * exit_point
    changes = []
    moment = registered_at
    while True:
        moment += timedelta(days=rng.expovariate(0.6 / 365))
        if moment > horizon or (end_at is not None and moment >= end_at):
            break
        changes.append(CustomerChange(moment, CHANGE_KINDS(rng)))
    if end_at is not None:
        changes.append(CustomerChange(end_at, end_kind))
    return tuple(changes), end_at


def _make_customer(config: SimulationConfig, index: int, registered_at: datetime) -> Customer:
    rng = make_rng(config.seed, "customer", index)
    is_b2b = rng.random() < 0.08
    male = rng.random() < 0.5
    first = rng.choice(ref.MALE_FIRST_NAMES if male else ref.FEMALE_FIRST_NAMES)
    surname_male, surname_female = rng.choice(ref.SURNAMES)
    last = surname_male if male else surname_female
    city = CITY_PICKER(rng)
    postal_code = f"{city.postal_prefix}-{rng.randrange(1000):03d}"
    email = make_email(rng, first, last, config.chaos.dirty_value_rate)
    phone, phone_style = random_phone(rng), PHONE_STYLES(rng)
    company = tax_id = birth_date = None
    if is_b2b:
        company = f"{rng.choice(ref.COMPANY_WORDS)} {surname_male} {rng.choice(ref.COMPANY_FORMS)}".strip()
        tax_id = _nip(rng)
        if rng.random() < config.chaos.dirty_value_rate:  # typo: checksum no longer valid
            tax_id = tax_id[:-1] + str((int(tax_id[-1]) + 1) % 10)
    else:
        birth_date = registered_at.date() - timedelta(days=rng.randint(18 * 365, 75 * 365))
    channel = REGISTRATION_CHANNELS(rng)
    if channel == "APP" and registered_at.date() < APP_LAUNCH:
        channel = "WEB"
    has_card = not is_b2b and rng.random() < 0.45
    tier = rng.choice(("SILVER", "SILVER", "GOLD")) if has_card else "NONE"
    consent = rng.random() < 0.58
    weight = min(50.0, rng.paretovariate(1.3)) * (3.0 if is_b2b else 1.0)
    changes, end_at = _timeline(rng, registered_at, config)
    return Customer(
        index, uuid_from(make_rng(config.seed, "customer-id", index)), "B2B" if is_b2b else "B2C",
        first, last, company, tax_id, email, phone, phone_style, birth_date, city.name, postal_code, channel,
        registered_at, loyalty_card_number(index) if has_card else None, tier, consent, weight, changes, end_at,
    )


def build_customers(config: SimulationConfig) -> list[Customer]:
    return [_make_customer(config, index, moment) for index, moment in enumerate(_registration_moments(config))]


def initial_state(customer: Customer) -> dict:
    return {
        "customer_id": customer.customer_id, "customer_type": customer.customer_type,
        "first_name": customer.first_name, "last_name": customer.last_name,
        "company_name": customer.company_name, "tax_id": customer.tax_id, "email": customer.email,
        "phone_digits": customer.phone_digits, "phone_style": customer.phone_style,
        "birth_date": customer.birth_date, "city": customer.city, "postal_code": customer.postal_code,
        "registration_channel": customer.registration_channel, "registered_at": customer.registered_at,
        "loyalty_card_no": customer.loyalty_card_no, "loyalty_tier": customer.loyalty_tier,
        "marketing_consent": customer.marketing_consent, "is_anonymized": False,
    }


def apply_change(state: dict, customer: Customer, change_index: int, config: SimulationConfig) -> dict:
    kind = customer.changes[change_index].kind
    rng = make_rng(config.seed, "customer-change", customer.index, change_index)
    new = dict(state)
    if kind == "EMAIL":
        new["email"] = make_email(rng, new["first_name"], new["last_name"], config.chaos.dirty_value_rate)
    elif kind == "PHONE":
        new["phone_digits"], new["phone_style"] = random_phone(rng), PHONE_STYLES(rng)
    elif kind == "ADDRESS":
        city = CITY_PICKER(rng)
        new["city"], new["postal_code"] = city.name, f"{city.postal_prefix}-{rng.randrange(1000):03d}"
    elif kind == "CONSENT":
        new["marketing_consent"] = not new["marketing_consent"]
    elif kind == "LOYALTY" and new["customer_type"] == "B2C":
        if new["loyalty_card_no"] is None:
            new["loyalty_card_no"], new["loyalty_tier"] = loyalty_card_number(customer.index), "SILVER"
        else:
            new["loyalty_tier"] = "GOLD" if new["loyalty_tier"] == "SILVER" else "SILVER"
    elif kind == "ERASE":
        new.update(dict.fromkeys(PII_FIELDS))
        new.update(loyalty_tier="NONE", marketing_consent=False, is_anonymized=True)
    return new  # DELETE carries the last state unchanged


def state_after(customer: Customer, change_index: int, config: SimulationConfig) -> dict:
    """State after applying changes 0..change_index (-1 = as registered)."""
    state = initial_state(customer)
    for index in range(change_index + 1):
        state = apply_change(state, customer, index, config)
    return state


def state_before(customer: Customer, moment: datetime, config: SimulationConfig) -> dict:
    state = initial_state(customer)
    for index, change in enumerate(customer.changes):
        if change.at >= moment:
            break
        state = apply_change(state, customer, index, config)
    return state


# --------------------------------------------------------------------------- world


class DayContext:
    """What can be sold on a given day, with popularity weights and memoized prices."""

    def __init__(self, products: list[Product], day: date) -> None:
        self.day = day
        self.online = [p for p in products if p.is_sellable(day)]
        self.online_cum = list(accumulate(p.popularity for p in self.online))
        self.accessories = [p for p in self.online if p.is_accessory]
        self.accessory_cum = list(accumulate(p.popularity for p in self.accessories))
        self.store = [p for p in self.online if p.in_store_assortment]
        self.store_cum = list(accumulate(p.popularity for p in self.store))
        self._prices: dict[tuple[int, str], Decimal] = {}

    def price(self, product: Product, channel: str) -> Decimal:
        key = (product.product_id, channel)
        if key not in self._prices:
            self._prices[key] = product.price_on(self.day, channel)
        return self._prices[key]


class World:
    def __init__(self, config: SimulationConfig) -> None:
        self.config = config
        self.categories = build_categories()
        self.products = build_products(config, self.categories)
        self.locations = build_locations(config)
        self.stores = [loc for loc in self.locations if loc.location_type == "STORE"]
        self.store_by_code = {store.location_code: store for store in self.stores}
        self.customers = build_customers(config)
        self._registered_at = [c.registered_at for c in self.customers]
        self._customer_cum = list(accumulate(c.weight for c in self.customers))
        self._card_holders = [c for c in self.customers if c.loyalty_card_no]
        self._card_registered_at = [c.registered_at for c in self._card_holders]
        self.crm_events_by_day = self._index_crm_events()
        self._day_contexts: OrderedDict[date, DayContext] = OrderedDict()

    def _index_crm_events(self) -> dict[date, list[tuple[int, int]]]:
        """UTC day -> [(customer index, change index)]; change index -1 means registration."""
        go_live = at_utc(self.config.history_start, 0)
        by_day: dict[date, list[tuple[int, int]]] = defaultdict(list)
        for customer in self.customers:
            if customer.registered_at >= go_live:
                by_day[customer.registered_at.date()].append((customer.index, -1))
            for index, change in enumerate(customer.changes):
                if change.at >= go_live:
                    by_day[change.at.date()].append((customer.index, index))
        return by_day

    def pick_customer(self, rng: random.Random, moment: datetime) -> Customer | None:
        """A customer registered before `moment` and still active, biased towards heavy buyers."""
        upto = bisect_left(self._registered_at, moment)
        if upto == 0:
            return None
        for _ in range(5):
            customer = self.customers[pick_weighted(rng, self._customer_cum, upto)]
            if customer.end_at is None or customer.end_at > moment:
                return customer
        return None

    def pick_card_holder(self, rng: random.Random, moment: datetime) -> Customer | None:
        upto = bisect_left(self._card_registered_at, moment)
        if upto == 0:
            return None
        customer = self._card_holders[rng.randrange(upto)]
        return customer if customer.end_at is None or customer.end_at > moment else None

    def store_is_open(self, store: Location, day: date) -> bool:
        return store.is_open(day) and is_trading_day(day)

    def day_context(self, day: date) -> DayContext:
        context = self._day_contexts.get(day)
        if context is None:
            context = DayContext(self.products, day)
            self._day_contexts[day] = context
            if len(self._day_contexts) > DAY_CONTEXT_CACHE_SIZE:
                self._day_contexts.popitem(last=False)
        return context
