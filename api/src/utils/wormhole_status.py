"""Wormhole status calculation utilities.

These utilities support both cron-based automatic updates and manual client updates.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from database.enums import LifetimeStatus, MassStatus

# Default lifetime assumptions when wormhole type is unknown
DEFAULT_LIFETIME_HOURS = 24

# Threshold boundaries in hours
THRESHOLD_STABLE = 24  # >24h = STABLE
THRESHOLD_AGING = 24  # <24h = AGING
THRESHOLD_CRITICAL = 4  # <4h = CRITICAL
THRESHOLD_EOL = 1  # <1h = EOL


def calculate_lifetime_status(
    original_status: LifetimeStatus,
    status_timestamp: datetime,
    wormhole_lifetime_hours: int | None = None,
    current_time: datetime | None = None,
) -> LifetimeStatus:
    """Calculate the current lifetime status based on elapsed time.

    Args:
        original_status: The status when it was last set
        status_timestamp: When the status was last set/verified
        wormhole_lifetime_hours: The wormhole type's total lifetime (e.g., 16, 24)
        current_time: Current time (defaults to now UTC)

    Returns:
        The calculated current status
    """
    if current_time is None:
        current_time = datetime.now(UTC)

    elapsed = current_time - status_timestamp
    elapsed_hours = elapsed.total_seconds() / 3600

    # Calculate remaining hours based on when status was set
    if original_status == LifetimeStatus.STABLE:
        # Fresh wormhole: use full lifetime
        lifetime = wormhole_lifetime_hours or DEFAULT_LIFETIME_HOURS
        remaining = lifetime - elapsed_hours
    elif original_status == LifetimeStatus.AGING:
        # <24h when marked
        remaining = THRESHOLD_AGING - elapsed_hours
    elif original_status == LifetimeStatus.CRITICAL:
        # <4h when marked
        remaining = THRESHOLD_CRITICAL - elapsed_hours
    elif original_status == LifetimeStatus.EOL:
        # <1h when marked
        remaining = THRESHOLD_EOL - elapsed_hours
    else:
        remaining = THRESHOLD_AGING  # Fallback

    # Determine current status based on remaining time
    if remaining <= 0:
        return LifetimeStatus.EOL  # Should have collapsed
    if remaining < THRESHOLD_EOL:
        return LifetimeStatus.EOL
    if remaining < THRESHOLD_CRITICAL:
        return LifetimeStatus.CRITICAL
    if remaining < THRESHOLD_AGING:
        return LifetimeStatus.AGING
    return LifetimeStatus.STABLE


def next_lifetime_status(current_status: LifetimeStatus) -> LifetimeStatus:
    """Get the next degraded lifetime status.

    Args:
        current_status: The current status

    Returns:
        The next more critical status, or EOL if already EOL
    """
    progression = {
        LifetimeStatus.STABLE: LifetimeStatus.AGING,
        LifetimeStatus.AGING: LifetimeStatus.CRITICAL,
        LifetimeStatus.CRITICAL: LifetimeStatus.EOL,
        LifetimeStatus.EOL: LifetimeStatus.EOL,
    }
    return progression[current_status]


def estimate_eol_time(
    lifetime_status: LifetimeStatus,
    status_timestamp: datetime,
    wormhole_lifetime_hours: int | None = None,
) -> datetime | None:
    """Estimate the end-of-life time based on status and when it was set.

    Args:
        lifetime_status: Current lifetime status
        status_timestamp: When the status was set
        wormhole_lifetime_hours: The wormhole's total lifetime

    Returns:
        Estimated collapse time, or None if unknown
    """
    if lifetime_status == LifetimeStatus.STABLE:
        if wormhole_lifetime_hours is None:
            return None  # Can't calculate without knowing wormhole type
        remaining_hours = wormhole_lifetime_hours
    elif lifetime_status == LifetimeStatus.AGING:
        remaining_hours = THRESHOLD_AGING
    elif lifetime_status == LifetimeStatus.CRITICAL:
        remaining_hours = THRESHOLD_CRITICAL
    elif lifetime_status == LifetimeStatus.EOL:
        remaining_hours = THRESHOLD_EOL
    else:
        return None

    return status_timestamp + timedelta(hours=remaining_hours)


def calculate_mass_usage(
    mass_remaining: int | None,
    mass_total: int | None,
) -> MassStatus:
    """Calculate mass status from raw values.

    Args:
        mass_remaining: Current remaining mass in kg
        mass_total: Total mass capacity in kg

    Returns:
        The appropriate mass status
    """
    if mass_remaining is None or mass_total is None or mass_total == 0:
        return MassStatus.STABLE  # Unknown, assume stable

    percentage = (mass_remaining / mass_total) * 100
    return calculate_mass_usage_from_percentage(percentage)


def calculate_mass_usage_from_percentage(mass_percentage: float) -> MassStatus:
    """Calculate mass status from remaining mass percentage.

    Args:
        mass_percentage: Remaining mass as percentage (0-100)

    Returns:
        The appropriate mass status
    """
    if mass_percentage > 50:
        return MassStatus.STABLE
    if mass_percentage > 10:
        return MassStatus.DESTABILIZED
    return MassStatus.CRITICAL


def next_mass_usage(current_status: MassStatus) -> MassStatus:
    """Get the next degraded mass status.

    Args:
        current_status: The current status

    Returns:
        The next more critical status, or CRITICAL if already CRITICAL
    """
    progression = {
        MassStatus.STABLE: MassStatus.DESTABILIZED,
        MassStatus.DESTABILIZED: MassStatus.CRITICAL,
        MassStatus.CRITICAL: MassStatus.CRITICAL,
    }
    return progression[current_status]
