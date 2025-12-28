"""Database enums for wormhole tracking."""
from __future__ import annotations

from enum import StrEnum


class LifetimeStatus(StrEnum):
    """Wormhole lifetime status indicators.

    Based on EVE Online wormhole lifetime mechanics where wormholes
    typically last 16-24 hours from spawn.
    """

    STABLE = "stable"  # >24 hours remaining (fresh wormhole)
    AGING = "aging"  # <24 hours remaining
    CRITICAL = "critical"  # <4 hours remaining
    EOL = "eol"  # <1 hour remaining (End of Life)


class MassStatus(StrEnum):
    """Wormhole mass status indicators.

    Based on EVE Online wormhole mass mechanics where wormholes
    collapse after a certain amount of mass passes through.
    """

    STABLE = "stable"  # >50% mass remaining
    DESTABILIZED = "destabilized"  # 10-50% mass remaining
    CRITICAL = "critical"  # <10% mass remaining (verge of collapse)
