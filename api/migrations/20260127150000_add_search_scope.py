"""Add search scope tracking to refresh_token
Description: Add boolean column to track search scope for characters
Version: 20260127150000
Created: 2026-01-27T15:00:00+00:00
Author: Jordan Russell <jordan@artek.nz>"""

from collections.abc import Iterable


async def up(context: object | None = None) -> str | Iterable[str]:
    """Apply the migration (upgrade)."""
    return [
        """
        ALTER TABLE refresh_token
        ADD COLUMN IF NOT EXISTS has_search_scope BOOLEAN NOT NULL DEFAULT FALSE;
        """,
    ]


async def down(context: object | None = None) -> str | Iterable[str]:
    """Reverse the migration."""
    return [
        "ALTER TABLE refresh_token DROP COLUMN IF EXISTS has_search_scope;",
    ]
