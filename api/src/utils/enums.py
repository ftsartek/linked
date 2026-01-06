"""Database enums for wormhole tracking."""

from __future__ import annotations

from enum import StrEnum


class LifetimeStatus(StrEnum):
    """Wormhole lifetime status indicators.

    Based on EVE Online wormhole lifetime mechanics where wormholes
    typically last 16-24 hours from spawn.
    """

    STABLE = "stable"  # >24 hours remaining (fresh/stable wormhole)
    AGING = "aging"  # <24 hours remaining (aging wormhole)
    CRITICAL = "critical"  # <4 hours remaining (critical wormhole)
    EOL = "eol"  # <1 hour remaining (End of Life)


class MassStatus(StrEnum):
    """Wormhole mass status indicators.

    Based on EVE Online wormhole mass mechanics where wormholes
    collapse after a certain amount of mass passes through.
    """

    STABLE = "stable"  # >50% mass remaining
    DESTABILIZED = "destabilized"  # 10-50% mass remaining
    CRITICAL = "critical"  # <10% mass remaining (verge of collapse)


class EdgeType(StrEnum):
    """Svelte Flow ConnectionLineType values."""

    DEFAULT = "default"  # bezier curves
    STRAIGHT = "straight"
    STEP = "step"
    SMOOTHSTEP = "smoothstep"
    SIMPLEBEZIER = "simplebezier"


class RankDir(StrEnum):
    """Dagre rankdir layout direction values."""

    TB = "TB"  # top to bottom (vertical)
    BT = "BT"  # bottom to top
    LR = "LR"  # left to right (horizontal)
    RL = "RL"  # right to left
