"""CRM customers as a CDC feed (JSON Lines): initial snapshot on go-live, then I/U/D events.

v2: _op becomes Debezium-style c/u/d (r for snapshots) - a delete filter on _op = 'D' silently
stops working; phone becomes a struct; new column preferred_store_code.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from .chaos import lateness, with_duplicates
from .formats import format_phone, iso_utc
from .rng import make_rng
from .world import World, at_utc, initial_state, state_after, state_before
from .writers import OutputFile

MAX_DELAY_DAYS = 2
OPS = {
    "v1": {"SNAPSHOT": "I", "I": "I", "U": "U", "D": "D"},
    "v2": {"SNAPSHOT": "r", "I": "c", "U": "u", "D": "d"},
}


@dataclass(frozen=True, slots=True)
class CrmEvent:
    is_late: bool
    commit_ts: datetime
    customer_index: int
    change_index: int  # -2 snapshot, -1 registration, >= 0 timeline change
    op: str  # SNAPSHOT | I | U | D
    state: dict


def crm_files(world: World, day: date, version: str) -> list[OutputFile]:
    config = world.config
    if day < config.history_start:
        return []
    events = _initial_snapshot(world) if day == config.history_start else []
    for back in range(MAX_DELAY_DAYS, -1, -1):
        origin = day - timedelta(days=back)
        if origin < config.history_start:
            continue
        for customer_index, change_index in world.crm_events_by_day.get(origin, ()):
            delay = lateness(config, "crm", f"{customer_index}#{change_index}")
            if origin + timedelta(days=delay) == day:
                events.append(_event(world, customer_index, change_index, is_late=delay > 0))
    # on-time events in commit order, late ones appended at the end (out of order, as in real CDC)
    events.sort(key=lambda e: (e.is_late, e.commit_ts, e.customer_index, e.change_index))
    records = [_serialize(world, event, version) for event in events]
    _corrupt_birth_dates(records, config.chaos.type_corruption_rate, make_rng(config.seed, "chaos-corrupt", "crm", day))
    records = with_duplicates(records, config.chaos.duplicate_rate, make_rng(config.seed, "chaos-dup", "crm", day))
    return [OutputFile("crm", "customer_cdc", day, f"customer_cdc_{day:%Y%m%d}.jsonl", "jsonl", records)]


def _initial_snapshot(world: World) -> list[CrmEvent]:
    go_live = at_utc(world.config.history_start, 0)
    events = []
    for customer in world.customers:  # sorted by registration time
        if customer.registered_at >= go_live:
            break
        deleted_before = (customer.end_at is not None and customer.end_at < go_live
                          and customer.changes[-1].kind == "DELETE")
        if not deleted_before:
            state = state_before(customer, go_live, world.config)
            events.append(CrmEvent(False, go_live, customer.index, -2, "SNAPSHOT", state))
    return events


def _event(world: World, customer_index: int, change_index: int, is_late: bool) -> CrmEvent:
    customer = world.customers[customer_index]
    if change_index == -1:
        return CrmEvent(is_late, customer.registered_at, customer_index, -1, "I", initial_state(customer))
    change = customer.changes[change_index]
    if change.kind == "DELETE":  # the delete event carries the last known row image
        state = state_after(customer, change_index - 1, world.config)
        return CrmEvent(is_late, change.at, customer_index, change_index, "D", state)
    state = state_after(customer, change_index, world.config)
    return CrmEvent(is_late, change.at, customer_index, change_index, "U", state)


def _serialize(world: World, event: CrmEvent, version: str) -> dict:
    state = event.state
    digits = state["phone_digits"]
    if digits is None:
        phone = None
    elif version == "v1":
        phone = format_phone(digits, state["phone_style"])
    else:
        phone = {"country_code": "+1", "number": digits}
    record = {
        "_op": OPS[version][event.op],
        "_commit_ts": iso_utc(event.commit_ts),
        "customer_id": state["customer_id"],
        "customer_type": state["customer_type"],
        "first_name": state["first_name"],
        "last_name": state["last_name"],
        "company_name": state["company_name"],
        "tax_id": state["tax_id"],
        "email": state["email"],
        "phone": phone,
        "birth_date": state["birth_date"].isoformat() if state["birth_date"] else None,
        "city": state["city"],
        "postal_code": state["postal_code"],
        "registration_channel": state["registration_channel"],
        "registered_at": iso_utc(state["registered_at"]),
        "loyalty_card_no": state["loyalty_card_no"],
        "loyalty_tier": state["loyalty_tier"],
        "marketing_consent": state["marketing_consent"],
        "is_anonymized": state["is_anonymized"],
    }
    if version == "v2":
        record["preferred_store_code"] = _preferred_store(world, event.customer_index, state["city"])
    return record


def _preferred_store(world: World, customer_index: int, city: str | None) -> str | None:
    rng = make_rng(world.config.seed, "crm-v2-store", customer_index)
    local_stores = [store.location_code for store in world.stores if store.city == city]
    roll = rng.random()
    return rng.choice(local_stores) if local_stores and roll < 0.6 else None


def _corrupt_birth_dates(records: list[dict], rate: float, rng) -> None:
    """Daily chaos: a front-end bug sends birth_date in the US display format."""
    if rate <= 0:
        return
    for record in records:
        if record["birth_date"] and rng.random() < rate:
            year, month, day = record["birth_date"].split("-")
            record["birth_date"] = rng.choice((f"{month}/{day}/{year}", f"{int(month)}/{int(day)}/{year[2:]}"))
