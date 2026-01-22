"""Add instance ACL tables
Description: Add instance-level access control with owner/admin roles and character/corporation/alliance ACLs
Version: 20260119205640
Created: 2026-01-19T20:56:40+00:00
Author: Jordan Russell <jordan@artek.nz>"""

from collections.abc import Iterable


async def up(context: object | None = None) -> str | Iterable[str]:
    """Apply the migration (upgrade)."""
    return [
        # Instance settings singleton table
        # Stores the instance owner and open/closed state
        """\
        CREATE TABLE IF NOT EXISTS instance_settings (
            id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
            owner_id UUID NOT NULL REFERENCES "user"(id),
            is_open BOOLEAN NOT NULL DEFAULT FALSE,
            date_created TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            date_updated TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """,
        # Admin users table (owner is stored in instance_settings, not here)
        """\
        CREATE TABLE IF NOT EXISTS instance_admin (
            user_id UUID PRIMARY KEY REFERENCES "user"(id) ON DELETE CASCADE,
            granted_by UUID REFERENCES "user"(id) ON DELETE SET NULL,
            date_created TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_instance_admin_granted_by ON instance_admin(granted_by);",
        # Character ACL table (standalone - no FK to character table)
        # Stores character info directly so ACL can filter before entities exist locally
        """\
        CREATE TABLE IF NOT EXISTS instance_acl_character (
            character_id BIGINT PRIMARY KEY,
            character_name TEXT NOT NULL,
            added_by UUID REFERENCES "user"(id) ON DELETE SET NULL,
            date_created TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_instance_acl_character_added_by ON instance_acl_character(added_by);",
        # Corporation ACL table (standalone - no FK to corporation table)
        """\
        CREATE TABLE IF NOT EXISTS instance_acl_corporation (
            corporation_id BIGINT PRIMARY KEY,
            corporation_name TEXT NOT NULL,
            corporation_ticker TEXT NOT NULL,
            added_by UUID REFERENCES "user"(id) ON DELETE SET NULL,
            date_created TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_instance_acl_corporation_added_by ON instance_acl_corporation(added_by);",
        # Alliance ACL table (standalone - no FK to alliance table)
        """\
        CREATE TABLE IF NOT EXISTS instance_acl_alliance (
            alliance_id BIGINT PRIMARY KEY,
            alliance_name TEXT NOT NULL,
            alliance_ticker TEXT NOT NULL,
            added_by UUID REFERENCES "user"(id) ON DELETE SET NULL,
            date_created TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_instance_acl_alliance_added_by ON instance_acl_alliance(added_by);",
    ]


async def down(context: object | None = None) -> str | Iterable[str]:
    """Reverse the migration."""
    return [
        "DROP TABLE IF EXISTS instance_acl_alliance CASCADE;",
        "DROP TABLE IF EXISTS instance_acl_corporation CASCADE;",
        "DROP TABLE IF EXISTS instance_acl_character CASCADE;",
        "DROP TABLE IF EXISTS instance_admin CASCADE;",
        "DROP TABLE IF EXISTS instance_settings CASCADE;",
    ]
