"""ERP master data: a daily FULL snapshot per table, as Parquet (the typed, "easy" source).

v2 (product only): vat_rate 0.23 -> 23.00 (same type, different meaning), weight_kg -> weight_g,
new column energy_class. Category and location files do not change.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal

from .formats import UTC, pl_amount
from .rng import make_rng
from .world import VAT_RATE, Category, Location, Product, World, at_utc
from .writers import OutputFile

CATEGORY_SCHEMA = (
    ("category_id", "int32"), ("parent_category_id", "int32"), ("category_code", "string"),
    ("category_name", "string"), ("category_level", "int8"), ("is_active", "bool"), ("updated_at", "timestamp"),
)
LOCATION_SCHEMA = (
    ("location_id", "int32"), ("location_code", "string"), ("location_name", "string"), ("location_type", "string"),
    ("store_format", "string"), ("city", "string"), ("voivodeship", "string"), ("postal_code", "string"),
    ("latitude", "decimal(9,6)"), ("longitude", "decimal(9,6)"), ("floor_area_m2", "int32"),
    ("opened_date", "date"), ("closed_date", "date"), ("updated_at", "timestamp"),
)
_PRODUCT_HEAD = (
    ("product_id", "int64"), ("sku", "string"), ("ean", "string"), ("product_name", "string"),
    ("brand_name", "string"), ("category_id", "int32"), ("primary_supplier_id", "int32"),
    ("vat_rate", "decimal(4,2)"), ("standard_cost_net", "decimal(18,2)"),
)
_PRODUCT_TAIL = (
    ("warranty_months", "int16"), ("launch_date", "date"), ("eol_date", "date"), ("status", "string"),
    ("created_at", "timestamp"), ("updated_at", "timestamp"),
)
PRODUCT_SCHEMA = {
    "v1": _PRODUCT_HEAD + (("weight_kg", "decimal(8,3)"),) + _PRODUCT_TAIL,
    "v2": _PRODUCT_HEAD + (("weight_g", "int32"), ("energy_class", "string")) + _PRODUCT_TAIL,
}
EOL_ANNOUNCED_DAYS = 90
CLOSURE_ANNOUNCED_DAYS = 30


def erp_files(world: World, day: date, version: str) -> list[OutputFile]:
    stamp = f"{day:%Y%m%d}"
    end_of_day = datetime.combine(day, time(23, 59, 59), tzinfo=UTC)
    products = [_product_row(p, day, version) for p in world.products if p.created_at <= end_of_day]
    products, product_schema = _maybe_export_cost_as_text(world, day, products, PRODUCT_SCHEMA[version])
    return [
        OutputFile("erp", "category", day, f"category_{stamp}.parquet", "parquet",
                   [_category_row(c, day) for c in world.categories], CATEGORY_SCHEMA),
        OutputFile("erp", "product", day, f"product_{stamp}.parquet", "parquet", products, product_schema),
        OutputFile("erp", "location", day, f"location_{stamp}.parquet", "parquet",
                   [_location_row(loc, day) for loc in world.locations if loc.created_at <= end_of_day],
                   LOCATION_SCHEMA),
    ]


def _category_row(category: Category, day: date) -> dict:
    return {
        "category_id": category.category_id, "parent_category_id": category.parent_category_id,
        "category_code": category.category_code, "category_name": category.name_on(day),
        "category_level": category.category_level, "is_active": True, "updated_at": category.updated_at_on(day),
    }


def _product_row(product: Product, day: date, version: str) -> dict:
    status, status_changed_at = product.status_on(day)
    cost = product.standard_cost_on(day)
    changed = [product.created_at, status_changed_at]
    if cost is not None:
        changed.append(product.cost_changed_at(day))  # cost is re-calculated monthly -> SCD2 churn
    eol_known = product.eol_date is not None and day >= product.eol_date - timedelta(days=EOL_ANNOUNCED_DAYS)
    if eol_known:
        changed.append(at_utc(product.eol_date - timedelta(days=EOL_ANNOUNCED_DAYS), 7))
    row = {
        "product_id": product.product_id, "sku": product.sku, "ean": product.ean, "product_name": product.name,
        "brand_name": product.brand_name, "category_id": product.category_id, "primary_supplier_id": None,
        "vat_rate": VAT_RATE if version == "v1" else Decimal("23.00"), "standard_cost_net": cost,
    }
    if version == "v1":
        row["weight_kg"] = product.weight_kg
    else:
        row["weight_g"] = int(product.weight_kg * 1000)
        row["energy_class"] = product.energy_class
    row.update(
        warranty_months=product.warranty_months, launch_date=product.launch_date,
        eol_date=product.eol_date if eol_known else None, status=status,
        created_at=product.created_at, updated_at=max(changed),
    )
    return row


def _location_row(location: Location, day: date) -> dict:
    closure_known = (location.closed_date is not None
                     and day >= location.closed_date - timedelta(days=CLOSURE_ANNOUNCED_DAYS))
    updated_at = (at_utc(location.closed_date - timedelta(days=CLOSURE_ANNOUNCED_DAYS), 7)
                  if closure_known else location.created_at)
    return {
        "location_id": location.location_id, "location_code": location.location_code,
        "location_name": location.location_name, "location_type": location.location_type,
        "store_format": location.store_format, "city": location.city, "voivodeship": location.voivodeship,
        "postal_code": location.postal_code, "latitude": location.latitude, "longitude": location.longitude,
        "floor_area_m2": location.floor_area_m2, "opened_date": location.opened_date,
        "closed_date": location.closed_date if closure_known else None, "updated_at": updated_at,
    }


def _maybe_export_cost_as_text(world: World, day: date, rows: list[dict], schema: tuple) -> tuple[list[dict], tuple]:
    """Chaos: on a bad day the ERP export writes standard_cost_net as '1 234,56 PLN' (whole file)."""
    rate = world.config.chaos.parquet_type_drift_rate
    if rate <= 0 or make_rng(world.config.seed, "chaos-erp-drift", day).random() >= rate:
        return rows, schema
    for row in rows:
        cost = row["standard_cost_net"]
        row["standard_cost_net"] = None if cost is None else f"{pl_amount(cost)} PLN"
    return rows, tuple((name, "string" if name == "standard_cost_net" else kind) for name, kind in schema)
