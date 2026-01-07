from contextlib import AbstractAsyncContextManager

from sqlspec import SQLSpec
from sqlspec.adapters.asyncpg import AsyncpgConfig, AsyncpgPoolConfig
from sqlspec.adapters.asyncpg.driver import AsyncpgDriver

from config.settings import get_settings
from database.models.alliance import CREATE_STMT as ALLIANCE_CREATE
from database.models.character import CREATE_STMT as CHARACTER_CREATE
from database.models.constellation import CREATE_STMT as CONSTELLATION_CREATE
from database.models.corporation import CREATE_STMT as CORPORATION_CREATE
from database.models.effect import CREATE_STMT as EFFECT_CREATE
from database.models.link import CREATE_STMT as LINK_CREATE
from database.models.map import CREATE_STMT as MAP_CREATE
from database.models.map_alliance import CREATE_STMT as MAP_ALLIANCE_CREATE
from database.models.map_character import CREATE_STMT as MAP_CHARACTER_CREATE
from database.models.map_corporation import CREATE_STMT as MAP_CORPORATION_CREATE
from database.models.map_subscription import CREATE_STMT as MAP_SUBSCRIPTION_CREATE
from database.models.node import CREATE_STMT as NODE_CREATE
from database.models.refresh_token import CREATE_STMT as REFRESH_TOKEN_CREATE

# Static EVE data tables
from database.models.region import CREATE_STMT as REGION_CREATE
from database.models.signature import CREATE_STMT as SIGNATURE_CREATE
from database.models.system import CREATE_STMT as SYSTEM_CREATE
from database.models.system_static import CREATE_STMT as SYSTEM_STATIC_CREATE

# Dynamic application tables
from database.models.user import CREATE_STMT as USER_CREATE
from database.models.wormhole import CREATE_STMT as WORMHOLE_CREATE

# PostgreSQL extensions
EXTENSIONS_STMT = "CREATE EXTENSION IF NOT EXISTS pg_trgm;"

# Shared trigger function for auto-updating date_updated
TRIGGER_UPDATED_AT_STMT = """\
CREATE OR REPLACE FUNCTION trigger_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.date_updated = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

# Table creation order (respects foreign key dependencies)
CREATE_STATEMENTS = [
    # Static EVE data (no dependencies on dynamic tables)
    REGION_CREATE,
    CONSTELLATION_CREATE,
    EFFECT_CREATE,
    WORMHOLE_CREATE,
    SYSTEM_CREATE,
    SYSTEM_STATIC_CREATE,
    # Dynamic tables (order matters for FK dependencies)
    USER_CREATE,  # No dependencies
    CORPORATION_CREATE,  # No dependencies (alliance_id is not FK)
    ALLIANCE_CREATE,  # No dependencies
    CHARACTER_CREATE,  # Depends on: user
    REFRESH_TOKEN_CREATE,  # Depends on: character
    MAP_CREATE,  # No dependencies
    MAP_CHARACTER_CREATE,  # Depends on: map, character
    MAP_CORPORATION_CREATE,  # Depends on: map, corporation
    MAP_ALLIANCE_CREATE,  # Depends on: map, alliance
    MAP_SUBSCRIPTION_CREATE,  # Depends on: map, user
    NODE_CREATE,  # Depends on: map, system
    LINK_CREATE,  # Depends on: map, node, wormhole
    SIGNATURE_CREATE,  # Depends on: node, map, link, wormhole
]

sql = SQLSpec()


def get_db_config() -> AsyncpgConfig:
    """Create database configuration from settings."""
    settings = get_settings()
    return AsyncpgConfig(
        connection_config=AsyncpgPoolConfig(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name,
            min_size=settings.db_pool_min_size,
            max_size=settings.db_pool_max_size,
            ssl=settings.db_ssl,
        ),
        extension_config={
            "litestar": {
                "session_key": "db_session",
            }
        },
    )


db = sql.add_config(get_db_config())


async def init_db() -> None:
    """Initialize database tables."""
    async with sql.provide_session(db) as session:
        # Enable required PostgreSQL extensions
        await session.execute(EXTENSIONS_STMT)
        # Create shared trigger function for date_updated
        await session.execute(TRIGGER_UPDATED_AT_STMT)
        for stmt in CREATE_STATEMENTS:
            await session.execute(stmt)


def provide_session() -> AbstractAsyncContextManager[AsyncpgDriver]:
    """Provide a database session context manager."""
    return sql.provide_session(db)
