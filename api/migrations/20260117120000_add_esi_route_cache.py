"""Add ESI route cache table
Description: Add ESI route cache table for storing k-space route data
Version: 20260117120000
Created: 2026-01-17T12:00:00.000000+00:00
Author: Jordan Russell <jordan@artek.nz>"""

from collections.abc import Iterable


async def up(context: object | None = None) -> str | Iterable[str]:
    """Apply the migration (upgrade)."""
    return [
        """\
CREATE TABLE IF NOT EXISTS esi_route_cache (
    id SERIAL PRIMARY KEY,
    origin_system_id INTEGER NOT NULL,
    destination_system_id INTEGER NOT NULL,
    route_type VARCHAR(10) NOT NULL,
    waypoints INTEGER[] NOT NULL,
    jump_count INTEGER NOT NULL,
    date_created TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    date_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(origin_system_id, destination_system_id, route_type)
);
""",
        "CREATE INDEX IF NOT EXISTS idx_esi_route_cache_origin ON esi_route_cache(origin_system_id);",
        "CREATE INDEX IF NOT EXISTS idx_esi_route_cache_destination ON esi_route_cache(destination_system_id);",
    ]


async def down(context: object | None = None) -> str | Iterable[str]:
    """Reverse the migration."""
    return [
        "DROP INDEX IF EXISTS idx_esi_route_cache_destination;",
        "DROP INDEX IF EXISTS idx_esi_route_cache_origin;",
        "DROP TABLE IF EXISTS esi_route_cache CASCADE;",
    ]
