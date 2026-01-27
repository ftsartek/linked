"""Add ship_type table
Description: Add table for ship type data used for location display
Version: 20260127120000
Created: 2026-01-27T12:00:00.000000+00:00
Author: Jordan Russell <jordan@artek.nz>"""

from collections.abc import Iterable


async def up(context: object | None = None) -> str | Iterable[str]:
    """Apply the migration (upgrade)."""
    return [
        """\
CREATE TABLE IF NOT EXISTS ship_type (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    group_id INTEGER NOT NULL
);
""",
        "CREATE INDEX IF NOT EXISTS idx_ship_type_name ON ship_type(name);",
        "CREATE INDEX IF NOT EXISTS idx_ship_type_group_id ON ship_type(group_id);",
    ]


async def down(context: object | None = None) -> str | Iterable[str]:
    """Reverse the migration."""
    return [
        "DROP TABLE IF EXISTS ship_type CASCADE;",
    ]
