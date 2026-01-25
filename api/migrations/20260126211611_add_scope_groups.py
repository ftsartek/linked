"""Add scope group tracking to refresh_token
Description: Add boolean columns to track enabled scope groups for characters
Version: 20260126211611
Created: 2026-01-26T21:16:11+00:00
Author: Jordan Russell <jordan@artek.nz>"""

from collections.abc import Iterable


async def up(context: object | None = None) -> str | Iterable[str]:
    """Apply the migration (upgrade)."""
    return [
        """
        ALTER TABLE refresh_token
        ADD COLUMN IF NOT EXISTS has_location_scope BOOLEAN NOT NULL DEFAULT FALSE;
        """,
        """
        ALTER TABLE map
        ADD COLUMN IF NOT EXISTS location_tracking_enabled BOOLEAN NOT NULL DEFAULT TRUE;
        """,
    ]


async def down(context: object | None = None) -> str | Iterable[str]:
    """Reverse the migration."""
    return [
        "ALTER TABLE map DROP COLUMN IF EXISTS location_tracking_enabled;",
        "ALTER TABLE refresh_token DROP COLUMN IF EXISTS has_location_scope;",
    ]
