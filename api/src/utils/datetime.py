"""Datetime utilities with timezone enforcement."""
from __future__ import annotations

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Get current UTC datetime with timezone info."""
    return datetime.now(UTC)


def ensure_utc(dt: datetime | None) -> datetime | None:
    """Ensure a datetime is UTC-aware.

    Args:
        dt: A datetime object (may be naive or aware)

    Returns:
        UTC-aware datetime or None
    """
    if dt is None:
        return None

    if dt.tzinfo is None:
        # Assume naive datetimes are UTC
        return dt.replace(tzinfo=UTC)

    # Convert to UTC if in different timezone
    return dt.astimezone(UTC)
