"""Add Map soft-delete
Description: Add Map soft-delete
Version: 20260108183524
Created: 2026-01-08T18:35:24.421997+00:00
Author: Jordan Russell <jordan@artek.nz>"""

from collections.abc import Iterable


async def up(context: object | None = None) -> str | Iterable[str]:
    """Apply the migration (upgrade)."""
    return """
    ALTER TABLE map ADD COLUMN date_deleted TIMESTAMPTZ;
    CREATE INDEX IF NOT EXISTS idx_map_date_deleted ON map(date_deleted);
    """


async def down(context: object | None = None) -> str | Iterable[str]:
    """Reverse the migration."""
    return """
    DROP INDEX IF EXISTS idx_map_date_deleted;
    ALTER TABLE map DROP COLUMN date_deleted;
    """
