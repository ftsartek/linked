from sqlspec import SQLSpec
from sqlspec.adapters.asyncpg import AsyncpgConfig, AsyncpgPoolConfig

from config.settings import get_settings

from database.models.region import CREATE_STMT as REGION_CREATE
from database.models.constellation import CREATE_STMT as CONSTELLATION_CREATE
from database.models.effect import CREATE_STMT as EFFECT_CREATE
from database.models.wormhole import CREATE_STMT as WORMHOLE_CREATE
from database.models.system import CREATE_STMT as SYSTEM_CREATE
from database.models.system_static import CREATE_STMT as SYSTEM_STATIC_CREATE

# Table creation order (respects foreign key dependencies)
CREATE_STATEMENTS = [
    REGION_CREATE,
    CONSTELLATION_CREATE,
    EFFECT_CREATE,
    WORMHOLE_CREATE,
    SYSTEM_CREATE,
    SYSTEM_STATIC_CREATE,
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
        )
    )


db = sql.add_config(get_db_config())


async def init_db() -> None:
    """Initialize database tables."""
    async with sql.provide_session(db) as session:
        for stmt in CREATE_STATEMENTS:
            await session.execute(stmt)


def provide_session():
    """Provide a database session context manager."""
    return sql.provide_session(db)
