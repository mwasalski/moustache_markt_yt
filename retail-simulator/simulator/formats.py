"""Wire formats shared by the source systems."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

UTC = timezone.utc
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def iso_utc(moment: datetime) -> str:
    """2025-03-14T10:22:33.123Z"""
    return moment.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def epoch_millis(moment: datetime) -> int:
    return (moment - EPOCH) // timedelta(milliseconds=1)


def pl_amount(value: Decimal) -> str:
    """Decimal('1299.99') -> '1 299,99' (Polish locale: space as thousands separator, decimal comma)."""
    return f"{value:,.2f}".replace(",", " ").replace(".", ",")


def format_phone(digits: str, style: int) -> str:
    """The same number typed five ways, as people do in free-text CRM fields."""
    a, b, c = digits[:3], digits[3:6], digits[6:]
    return (f"+48 {a} {b} {c}", digits, f"{a}-{b}-{c}", f"0048{digits}", f"+48{digits}")[style]
