"""Add notes table
Description: Add notes table for per-system notes with optional expiry
Version: 20260119140000
Created: 2026-01-19T14:00:00.000000+00:00
Author: Jordan Russell <jordan@artek.nz>"""

from collections.abc import Iterable


async def up(context: object | None = None) -> str | Iterable[str]:
    """Apply the migration (upgrade)."""
    return """
    CREATE TABLE note (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        solar_system_id INT NOT NULL,
        map_id UUID NOT NULL REFERENCES map(id),
        title TEXT,
        content TEXT NOT NULL,
        created_by BIGINT NOT NULL REFERENCES character(id),
        updated_by BIGINT REFERENCES character(id),
        date_expires TIMESTAMPTZ,
        date_created TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        date_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        date_deleted TIMESTAMPTZ
    );

    CREATE INDEX idx_note_solar_system_id ON note(solar_system_id, map_id) WHERE date_deleted IS NULL;
    CREATE INDEX idx_note_map_id ON note(map_id) WHERE date_deleted IS NULL;
    CREATE INDEX idx_note_expires ON note(date_expires) WHERE date_deleted IS NULL AND date_expires IS NOT NULL;
    """


async def down(context: object | None = None) -> str | Iterable[str]:
    """Reverse the migration."""
    return """
    DROP TABLE IF EXISTS note;
    """
