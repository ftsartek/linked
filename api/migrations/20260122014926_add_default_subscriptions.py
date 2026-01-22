"""Add default subscriptions and map creation control
Description: Add default_map_subscription table and allow_map_creation column to instance_settings
Version: 20260122014926
Created: 2026-01-22T01:49:26+00:00
Author: Jordan Russell <jordan@artek.nz>"""

from collections.abc import Iterable


async def up(context: object | None = None) -> str | Iterable[str]:
    """Apply the migration (upgrade)."""
    return [
        # Add allow_map_creation column to instance_settings
        # When false, only admins/owner can create maps
        """\
        ALTER TABLE instance_settings
        ADD COLUMN IF NOT EXISTS allow_map_creation BOOLEAN NOT NULL DEFAULT TRUE;
        """,
        # Default map subscriptions table
        # Maps marked as default will auto-subscribe new users on signup
        """\
        CREATE TABLE IF NOT EXISTS default_map_subscription (
            map_id UUID PRIMARY KEY REFERENCES map(id) ON DELETE CASCADE,
            added_by UUID REFERENCES "user"(id) ON DELETE SET NULL,
            date_created TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_default_map_subscription_added_by ON default_map_subscription(added_by);",
    ]


async def down(context: object | None = None) -> str | Iterable[str]:
    """Reverse the migration."""
    return [
        "DROP TABLE IF EXISTS default_map_subscription CASCADE;",
        "ALTER TABLE instance_settings DROP COLUMN IF EXISTS allow_map_creation;",
    ]
