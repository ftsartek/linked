"""Add name column to npc_station
Description: Add name column to npc_station table for station name display
Version: 20260127140000
Created: 2026-01-27T14:00:00.000000+00:00
Author: Jordan Russell <jordan@artek.nz>"""

from collections.abc import Iterable


async def up(context: object | None = None) -> str | Iterable[str]:
    """Apply the migration (upgrade)."""
    return [
        "ALTER TABLE npc_station ADD COLUMN IF NOT EXISTS name TEXT;",
    ]


async def down(context: object | None = None) -> str | Iterable[str]:
    """Reverse the migration."""
    return [
        "ALTER TABLE npc_station DROP COLUMN IF EXISTS name;",
    ]
