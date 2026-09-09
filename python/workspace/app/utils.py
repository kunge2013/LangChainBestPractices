"""
Common utility functions.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from app.config import settings


def now_yyyymm() -> str:
    """Return current year-month as YYYYMM string."""
    return datetime.now().strftime("%Y%m")


def prev_month_yyyymm(base: datetime | None = None) -> str:
    """Return previous month as YYYYMM string."""
    dt = base or datetime.now()
    if dt.month == 1:
        return f"{dt.year - 1}12"
    return f"{dt.year}{dt.month - 1:02d}"


def current_staff_id() -> int:
    """Return current staff id (mocked for non-auth context)."""
    return settings.system_staff_id


def validate_yyyymm(value: str) -> bool:
    """Check that *value* is a 6-digit YYYYMM string."""
    if not value or len(value) != 6:
        return False
    try:
        year = int(value[:4])
        month = int(value[4:])
    except (ValueError, IndexError):
        return False
    return 1 <= year <= 9999 and 1 <= month <= 12


def safe_decimal(value) -> Decimal:
    """Safely convert to Decimal, returning 0 for None."""
    if value is None:
        return Decimal("0")
    return Decimal(str(value))
