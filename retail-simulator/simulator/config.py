"""Simulation settings. Anything that changes the generated data lives here."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date

SYSTEMS: tuple[str, ...] = ("erp", "crm", "ecom", "pos")
SCHEMA_VERSIONS: tuple[str, ...] = ("v1", "v2")


@dataclass(frozen=True)
class ChaosConfig:
    duplicate_rate: float = 0.002  # exact duplicate records within a file
    late_arrival_rate: float = 0.01  # records (or whole store files) delivered 1-2 days late
    dirty_value_rate: float = 0.03  # brand variants, invalid NIPs, messy e-mails, unknown barcodes
    type_corruption_rate: float = 0.0  # "$ 123" instead of a number - daily runs only, see cli.py
    parquet_type_drift_rate: float = 0.0  # an ERP file exports a numeric column as text


# Type corruption is OFF for the backfill on purpose: if history contained "$ 123",
# schema inference in episode 1 would silently widen those columns to STRING.
DAILY_CHAOS_OVERRIDES = {"type_corruption_rate": 0.003, "parquet_type_drift_rate": 0.05}


@dataclass(frozen=True)
class SimulationConfig:
    seed: int = 42
    scale: float = 1.0
    history_start: date = date(2025, 1, 1)  # exports go live; CRM sends its initial snapshot that day
    world_end: date = date(2027, 12, 31)  # fixed horizon, so data never depends on the requested --end
    products: int = 2_500
    initial_customers: int = 40_000
    new_customers_per_day: float = 55.0
    online_orders_per_day: float = 350.0
    receipts_per_store_per_day: float = 90.0
    chaos: ChaosConfig = field(default_factory=ChaosConfig)

    def with_chaos(self, **changes: float) -> SimulationConfig:
        return replace(self, chaos=replace(self.chaos, **changes))
