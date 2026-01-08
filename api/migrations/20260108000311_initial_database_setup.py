"""Initial database setup
Description: Initial database setup
Version: 20260108000311
Created: 2026-01-08T00:03:11.262237+00:00
Author: Jordan Russell <jordan@artek.nz>"""

from collections.abc import Iterable


async def up(context: object | None = None) -> str | Iterable[str]:
    """Apply the migration (upgrade)."""
    return [
        # Enable required PostgreSQL extensions
        "CREATE EXTENSION IF NOT EXISTS pg_trgm;",
        # Shared trigger function for auto-updating date_updated
        """\
    CREATE OR REPLACE FUNCTION trigger_updated_at()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.date_updated = NOW();
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """,
        # Static EVE data tables (no dependencies on dynamic tables)
        """\
    CREATE TABLE IF NOT EXISTS region (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        wormhole_class_id INTEGER,
        faction_id INTEGER
    );
    """,
        "CREATE INDEX IF NOT EXISTS idx_region_name ON region(name);",
        """\
    CREATE TABLE IF NOT EXISTS constellation (
        id INTEGER PRIMARY KEY,
        region_id INTEGER REFERENCES region(id),
        name TEXT NOT NULL,
        wormhole_class_id INTEGER,
        faction_id INTEGER
    );
    """,
        "CREATE INDEX IF NOT EXISTS idx_constellation_region_id ON constellation(region_id);",
        "CREATE INDEX IF NOT EXISTS idx_constellation_name ON constellation(name);",
        """\
    CREATE TABLE IF NOT EXISTS effect (
        id SERIAL PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        buffs JSONB,
        debuffs JSONB
    );
    """,
        """\
    CREATE TABLE IF NOT EXISTS wormhole (
        id SERIAL PRIMARY KEY,
        code TEXT UNIQUE NOT NULL,
        eve_type_id INTEGER,
        sources INTEGER[],
        target_class INTEGER,
        mass_total BIGINT,
        mass_jump_max BIGINT,
        mass_regen BIGINT,
        lifetime REAL,
        target_regions INTEGER[],
        target_constellations INTEGER[],
        target_systems INTEGER[]
    );
    """,
        "CREATE INDEX IF NOT EXISTS idx_wormhole_sources ON wormhole USING GIN (sources);",
        "CREATE INDEX IF NOT EXISTS idx_wormhole_target_class ON wormhole(target_class);",
        "CREATE INDEX IF NOT EXISTS idx_wormhole_code_trgm ON wormhole USING GIN (code gin_trgm_ops);",
        """\
    CREATE TABLE IF NOT EXISTS system (
        id INTEGER PRIMARY KEY,
        constellation_id INTEGER REFERENCES constellation(id),
        name TEXT NOT NULL,
        security_status REAL,
        security_class TEXT,
        system_class INTEGER,
        faction_id INTEGER,
        star_id INTEGER,
        radius REAL,
        pos_x REAL,
        pos_y REAL,
        stargate_ids INTEGER[],
        wh_effect_id INTEGER REFERENCES effect(id)
    );
    """,
        "CREATE INDEX IF NOT EXISTS idx_system_constellation_id ON system(constellation_id);",
        "CREATE INDEX IF NOT EXISTS idx_system_name ON system(name);",
        "CREATE INDEX IF NOT EXISTS idx_system_name_trgm ON system USING GIN (name gin_trgm_ops);",
        "CREATE INDEX IF NOT EXISTS idx_system_system_class ON system(system_class);",
        "CREATE INDEX IF NOT EXISTS idx_system_wh_effect_id ON system(wh_effect_id);",
        """\
    CREATE TABLE IF NOT EXISTS system_static (
        system_id INTEGER REFERENCES system(id) ON DELETE CASCADE,
        wormhole_id INTEGER REFERENCES wormhole(id) ON DELETE CASCADE,
        PRIMARY KEY (system_id, wormhole_id)
    );
    """,
        "CREATE INDEX IF NOT EXISTS idx_system_static_wormhole_id ON system_static(wormhole_id);",
        # Dynamic application tables
        """\
    CREATE TABLE IF NOT EXISTS "user" (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        primary_character_id BIGINT,
        date_created TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        date_updated TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """,
        'CREATE INDEX IF NOT EXISTS idx_user_date_created ON "user"(date_created);',
        """\
    CREATE TABLE IF NOT EXISTS corporation (
        id BIGINT PRIMARY KEY,
        name TEXT NOT NULL,
        ticker TEXT NOT NULL,
        alliance_id BIGINT,
        member_count INTEGER,
        date_created TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        date_updated TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """,
        "CREATE INDEX IF NOT EXISTS idx_corporation_alliance_id ON corporation(alliance_id);",
        "CREATE INDEX IF NOT EXISTS idx_corporation_name ON corporation(name);",
        "CREATE INDEX IF NOT EXISTS idx_corporation_ticker ON corporation(ticker);",
        "CREATE INDEX IF NOT EXISTS idx_corporation_name_trgm ON corporation USING GIN (name gin_trgm_ops);",
        "CREATE INDEX IF NOT EXISTS idx_corporation_ticker_trgm ON corporation USING GIN (ticker gin_trgm_ops);",
        """\
    CREATE TABLE IF NOT EXISTS alliance (
        id BIGINT PRIMARY KEY,
        name TEXT NOT NULL,
        ticker TEXT NOT NULL,
        date_created TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        date_updated TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """,
        "CREATE INDEX IF NOT EXISTS idx_alliance_name ON alliance(name);",
        "CREATE INDEX IF NOT EXISTS idx_alliance_ticker ON alliance(ticker);",
        "CREATE INDEX IF NOT EXISTS idx_alliance_name_trgm ON alliance USING GIN (name gin_trgm_ops);",
        "CREATE INDEX IF NOT EXISTS idx_alliance_ticker_trgm ON alliance USING GIN (ticker gin_trgm_ops);",
        """\
    CREATE TABLE IF NOT EXISTS character (
        id BIGINT PRIMARY KEY,
        user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        corporation_id BIGINT,
        alliance_id BIGINT,
        date_created TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        date_updated TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """,
        "CREATE INDEX IF NOT EXISTS idx_character_user_id ON character(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_character_corporation_id ON character(corporation_id);",
        "CREATE INDEX IF NOT EXISTS idx_character_alliance_id ON character(alliance_id);",
        "CREATE INDEX IF NOT EXISTS idx_character_name ON character(name);",
        "CREATE INDEX IF NOT EXISTS idx_character_name_trgm ON character USING GIN (name gin_trgm_ops);",
        """\
    CREATE TABLE IF NOT EXISTS refresh_token (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        character_id BIGINT NOT NULL REFERENCES character(id) ON DELETE CASCADE,
        token BYTEA NOT NULL,
        scopes TEXT[] NOT NULL DEFAULT '{}',
        expires_at TIMESTAMPTZ,
        date_created TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        date_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE(character_id)
    );
    """,
        "CREATE INDEX IF NOT EXISTS idx_refresh_token_character_id ON refresh_token(character_id);",
        # Map tables
        """\
    CREATE TABLE IF NOT EXISTS map (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        owner_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        description TEXT,
        is_public BOOLEAN NOT NULL DEFAULT FALSE,
        public_read_only BOOLEAN NOT NULL DEFAULT TRUE,
        edge_type TEXT NOT NULL DEFAULT 'default',
        rankdir TEXT NOT NULL DEFAULT 'TB',
        auto_layout BOOLEAN NOT NULL DEFAULT FALSE,
        node_sep INTEGER NOT NULL DEFAULT 80,
        rank_sep INTEGER NOT NULL DEFAULT 60,
        date_created TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        date_updated TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """,
        "CREATE INDEX IF NOT EXISTS idx_map_owner_id ON map(owner_id);",
        "CREATE INDEX IF NOT EXISTS idx_map_name ON map(name);",
        "CREATE INDEX IF NOT EXISTS idx_map_is_public ON map(is_public);",
        "CREATE INDEX IF NOT EXISTS idx_map_date_created ON map(date_created);",
        """\
    CREATE TABLE IF NOT EXISTS map_character (
        map_id UUID NOT NULL REFERENCES map(id) ON DELETE CASCADE,
        character_id BIGINT NOT NULL REFERENCES character(id) ON DELETE CASCADE,
        read_only BOOLEAN NOT NULL DEFAULT true,
        PRIMARY KEY (map_id, character_id)
    );
    """,
        "CREATE INDEX IF NOT EXISTS idx_map_character_character_id ON map_character(character_id);",
        """\
    CREATE TABLE IF NOT EXISTS map_corporation (
        map_id UUID NOT NULL REFERENCES map(id) ON DELETE CASCADE,
        corporation_id BIGINT NOT NULL REFERENCES corporation(id) ON DELETE CASCADE,
        read_only BOOLEAN NOT NULL DEFAULT true,
        PRIMARY KEY (map_id, corporation_id)
    );
    """,
        "CREATE INDEX IF NOT EXISTS idx_map_corporation_corporation_id ON map_corporation(corporation_id);",
        "CREATE INDEX IF NOT EXISTS idx_map_corporation_read_only ON map_corporation(read_only);",
        """\
    CREATE TABLE IF NOT EXISTS map_alliance (
        map_id UUID NOT NULL REFERENCES map(id) ON DELETE CASCADE,
        alliance_id BIGINT NOT NULL REFERENCES alliance(id) ON DELETE CASCADE,
        read_only BOOLEAN NOT NULL DEFAULT true,
        PRIMARY KEY (map_id, alliance_id)
    );
    """,
        "CREATE INDEX IF NOT EXISTS idx_map_alliance_alliance_id ON map_alliance(alliance_id);",
        "CREATE INDEX IF NOT EXISTS idx_map_alliance_read_only ON map_alliance(read_only);",
        """\
    CREATE TABLE IF NOT EXISTS map_subscription (
        map_id UUID NOT NULL REFERENCES map(id) ON DELETE CASCADE,
        user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
        date_created TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        PRIMARY KEY (map_id, user_id)
    );
    """,
        "CREATE INDEX IF NOT EXISTS idx_map_subscription_user_id ON map_subscription(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_map_subscription_map_id ON map_subscription(map_id);",
        # Data tables
        """\
    CREATE TABLE IF NOT EXISTS node (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        map_id UUID NOT NULL REFERENCES map(id) ON DELETE CASCADE,
        system_id INTEGER NOT NULL REFERENCES system(id),
        pos_x REAL NOT NULL DEFAULT 0,
        pos_y REAL NOT NULL DEFAULT 0,
        locked BOOLEAN NOT NULL DEFAULT FALSE,
        label TEXT,
        date_created TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        date_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        date_deleted TIMESTAMPTZ
    );
    """,
        "CREATE INDEX IF NOT EXISTS idx_node_map_id ON node(map_id);",
        "CREATE INDEX IF NOT EXISTS idx_node_system_id ON node(system_id);",
        "CREATE INDEX IF NOT EXISTS idx_node_date_deleted ON node(date_deleted);",
        # Partial unique index: only enforce uniqueness for real systems (positive IDs)
        # Unidentified systems (negative IDs) can have multiple nodes per map
        """\
    CREATE UNIQUE INDEX IF NOT EXISTS idx_node_map_system_unique
    ON node(map_id, system_id)
    WHERE system_id > 0 AND date_deleted IS NULL;
    """,
        """\
    CREATE TABLE IF NOT EXISTS link (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        map_id UUID NOT NULL REFERENCES map(id) ON DELETE CASCADE,
        source_node_id UUID NOT NULL REFERENCES node(id) ON DELETE CASCADE,
        target_node_id UUID NOT NULL REFERENCES node(id) ON DELETE CASCADE,
        wormhole_id INTEGER REFERENCES wormhole(id),
        lifetime_status TEXT NOT NULL DEFAULT 'stable',
        date_lifetime_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        mass_usage BIGINT NOT NULL DEFAULT 0,
        date_mass_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        date_created TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        date_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        date_deleted TIMESTAMPTZ
    );
    """,
        """\
    CREATE UNIQUE INDEX IF NOT EXISTS idx_link_map_nodes_unique
    ON link(map_id, source_node_id, target_node_id)
    WHERE date_deleted IS NULL;
    """,
        "CREATE INDEX IF NOT EXISTS idx_link_map_id ON link(map_id);",
        "CREATE INDEX IF NOT EXISTS idx_link_source_node_id ON link(source_node_id);",
        "CREATE INDEX IF NOT EXISTS idx_link_target_node_id ON link(target_node_id);",
        "CREATE INDEX IF NOT EXISTS idx_link_wormhole_id ON link(wormhole_id);",
        "CREATE INDEX IF NOT EXISTS idx_link_lifetime_status ON link(lifetime_status);",
        "CREATE INDEX IF NOT EXISTS idx_link_mass_usage ON link(mass_usage);",
        "CREATE INDEX IF NOT EXISTS idx_link_date_deleted ON link(date_deleted);",
        """\
    CREATE TABLE IF NOT EXISTS signature (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        node_id UUID NOT NULL REFERENCES node(id) ON DELETE CASCADE,
        map_id UUID NOT NULL REFERENCES map(id) ON DELETE CASCADE,
        code TEXT NOT NULL,
        group_type TEXT NOT NULL,
        subgroup TEXT,
        type TEXT,
        link_id UUID REFERENCES link(id) ON DELETE SET NULL,
        wormhole_id INTEGER REFERENCES wormhole(id),
        date_created TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        date_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        date_deleted TIMESTAMPTZ
    );
    """,
        """\
    CREATE UNIQUE INDEX IF NOT EXISTS idx_signature_node_code_unique
    ON signature(node_id, code)
    WHERE date_deleted IS NULL;
    """,
        "CREATE INDEX IF NOT EXISTS idx_signature_node_id ON signature(node_id);",
        "CREATE INDEX IF NOT EXISTS idx_signature_map_id ON signature(map_id);",
        "CREATE INDEX IF NOT EXISTS idx_signature_link_id ON signature(link_id);",
        "CREATE INDEX IF NOT EXISTS idx_signature_wormhole_id ON signature(wormhole_id);",
        "CREATE INDEX IF NOT EXISTS idx_signature_date_deleted ON signature(date_deleted);",
        "DROP TRIGGER IF EXISTS trigger_signature_updated_at ON signature;",
        """\
    CREATE TRIGGER trigger_signature_updated_at
        BEFORE UPDATE ON signature
        FOR EACH ROW
        EXECUTE FUNCTION trigger_updated_at();
    """,
    ]


async def down(context: object | None = None) -> str | Iterable[str]:
    """Reverse the migration."""
    return [
        "DROP TRIGGER IF EXISTS trigger_signature_updated_at ON signature;",
        "DROP TABLE IF EXISTS signature CASCADE;",
        "DROP TABLE IF EXISTS link CASCADE;",
        "DROP TABLE IF EXISTS node CASCADE;",
        "DROP TABLE IF EXISTS map_subscription CASCADE;",
        "DROP TABLE IF EXISTS map_alliance CASCADE;",
        "DROP TABLE IF EXISTS map_corporation CASCADE;",
        "DROP TABLE IF EXISTS map_character CASCADE;",
        "DROP TABLE IF EXISTS map CASCADE;",
        "DROP TABLE IF EXISTS refresh_token CASCADE;",
        "DROP TABLE IF EXISTS character CASCADE;",
        "DROP TABLE IF EXISTS alliance CASCADE;",
        "DROP TABLE IF EXISTS corporation CASCADE;",
        'DROP TABLE IF EXISTS "user" CASCADE;',
        "DROP TABLE IF EXISTS system_static CASCADE;",
        "DROP TABLE IF EXISTS system CASCADE;",
        "DROP TABLE IF EXISTS wormhole CASCADE;",
        "DROP TABLE IF EXISTS effect CASCADE;",
        "DROP TABLE IF EXISTS constellation CASCADE;",
        "DROP TABLE IF EXISTS region CASCADE;",
        "DROP FUNCTION IF EXISTS trigger_updated_at();",
        "DROP EXTENSION IF EXISTS pg_trgm;",
    ]
