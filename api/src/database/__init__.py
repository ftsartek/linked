from contextlib import AbstractAsyncContextManager
from pathlib import Path

from sqlspec import SQLSpec
from sqlspec.adapters.asyncpg import AsyncpgConfig, AsyncpgPoolConfig
from sqlspec.adapters.asyncpg.driver import AsyncpgDriver

from config.settings import get_settings


def get_db_config() -> AsyncpgConfig:
    """Create database configuration from settings."""
    settings = get_settings()
    return AsyncpgConfig(
        connection_config=AsyncpgPoolConfig(
            dsn=settings.postgres.uri,
            min_size=settings.postgres.pool_min_size,
            max_size=settings.postgres.pool_max_size,
            ssl=settings.postgres.ssl,
        ),
        migration_config={
            "enabled": True,
            "script_location": Path(__file__).parent.parent.parent / "migrations",
            "version_table_name": "ddl_migrations",
        },
        extension_config={
            "litestar": {
                "session_key": "db_session",
            }
        },
    )


sql = SQLSpec()
db = sql.add_config(get_db_config())


def provide_session() -> AbstractAsyncContextManager[AsyncpgDriver]:
    """Provide a database session context manager."""
    return sql.provide_session(db)
