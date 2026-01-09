"""Root test configuration with session-scoped Docker containers and fixtures."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest
import pytest_asyncio
from litestar.testing import AsyncTestClient

if TYPE_CHECKING:
    from litestar import Litestar
    from sqlspec import SQLSpec
    from valkey.asyncio import Valkey

    from config.settings import Settings


# Configure pytest
def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest markers."""
    config.addinivalue_line("markers", "order: specify test execution order")


# pytest-docker configuration
@pytest.fixture(scope="session")
def docker_compose_file() -> Path:
    """Path to docker-compose file for test containers."""
    return Path(__file__).parent / "docker-compose.yml"


@pytest.fixture(scope="session")
def docker_compose_project_name() -> str:
    """Unique project name to avoid conflicts."""
    return "linked_test"


def is_postgres_responsive(host: str, port: int) -> bool:
    """Check if PostgreSQL is accepting connections."""
    import socket

    try:
        sock = socket.create_connection((host, port), timeout=1)
        sock.close()
        return True
    except OSError:
        return False


def is_valkey_responsive(host: str, port: int) -> bool:
    """Check if Valkey is accepting connections."""
    import socket

    try:
        sock = socket.create_connection((host, port), timeout=1)
        # Send PING command
        sock.sendall(b"*1\r\n$4\r\nPING\r\n")
        response = sock.recv(7)
        sock.close()
        return response == b"+PONG\r\n"
    except OSError:
        return False


@pytest.fixture(scope="session")
def test_db_port(docker_ip: str, docker_services: Any) -> int:
    """Get the mapped PostgreSQL port and wait for it to be responsive."""
    port = docker_services.port_for("postgres-test", 5432)
    docker_services.wait_until_responsive(
        timeout=30.0,
        pause=0.5,
        check=lambda: is_postgres_responsive(docker_ip, port),
    )
    return port


@pytest.fixture(scope="session")
def test_valkey_port(docker_ip: str, docker_services: Any) -> int:
    """Get the mapped Valkey port and wait for it to be responsive."""
    port = docker_services.port_for("valkey-test", 6379)
    docker_services.wait_until_responsive(
        timeout=30.0,
        pause=0.5,
        check=lambda: is_valkey_responsive(docker_ip, port),
    )
    return port


@pytest.fixture(scope="session")
def docker_ip() -> str:
    """Get Docker host IP."""
    return "127.0.0.1"


@pytest.fixture(scope="session")
def test_settings(docker_ip: str, test_db_port: int, test_valkey_port: int) -> Settings:
    """Create test settings with Docker service ports."""
    from config.settings import Settings

    return Settings(
        debug=True,
        csrf_secret="a" * 32,
        db_host=docker_ip,
        db_port=test_db_port,
        db_user="linked_test",
        db_password="linked_test",
        db_name="linked_test",
        db_ssl=False,
        db_pool_min_size=1,
        db_pool_max_size=5,
        valkey_host=docker_ip,
        valkey_port=test_valkey_port,
        valkey_password=None,
        esi_user_agent="LinkedTest/1.0",
        eve_client_id="test_client_id",
        eve_client_secret="test_client_secret",
        token_encryption_key="a" * 44,  # Placeholder value - token encryption not exercised in tests
    )


@pytest.fixture(scope="session")
def override_settings(test_settings: Settings) -> Generator[Settings]:
    """Override get_settings to return test settings."""
    from config import settings as settings_module

    # Clear any cached settings
    settings_module.get_settings.cache_clear()

    # Patch get_settings to return our test settings
    with patch.object(settings_module, "get_settings", return_value=test_settings):
        yield test_settings

    # Clear cache after tests
    settings_module.get_settings.cache_clear()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def db_config(
    override_settings: Settings,
) -> AsyncGenerator[tuple[SQLSpec, Any]]:
    """Create database configuration using test settings directly."""
    import sys
    from pathlib import Path

    from sqlspec import SQLSpec
    from sqlspec.adapters.asyncpg import AsyncpgConfig, AsyncpgPoolConfig

    settings = override_settings
    print(
        f"DEBUG: db_config using {settings.db_host}:{settings.db_port}/{settings.db_name}",
        file=sys.stderr,
    )

    # Create database config directly from test settings
    config = AsyncpgConfig(
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
        migration_config={
            "enabled": True,
            "script_location": Path(__file__).parent.parent / "migrations",
            "version_table_name": "ddl_migrations",
        },
        extension_config={
            "litestar": {
                "session_key": "db_session",
            }
        },
    )

    # Create a fresh SQLSpec instance for tests
    sql = SQLSpec()
    db = sql.add_config(config)

    # Run migrations
    print("DEBUG: Running migrations", file=sys.stderr)
    await db.migrate_up("head")
    print("DEBUG: Migrations complete", file=sys.stderr)

    yield sql, db

    # Cleanup - close pool
    await sql.close_pool(db)


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def db_engine(db_config: tuple[SQLSpec, Any]) -> SQLSpec:
    """Provide the SQLSpec instance."""
    sql, _ = db_config
    return sql


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def db(db_config: tuple[SQLSpec, Any]) -> Any:
    """Provide the database config for provide_session calls."""
    _, db = db_config
    return db


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def preseed_data(db_engine: SQLSpec, db: Any) -> None:
    """Insert curated test data into the database."""
    from tests.fixtures.preseed import preseed_test_data

    async with db_engine.provide_session(db) as session:
        await preseed_test_data(session)


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def valkey_client(override_settings: Settings) -> AsyncGenerator[Valkey]:
    """Provide Valkey client for tests."""
    import valkey.asyncio as valkey

    client = valkey.from_url(
        override_settings.valkey_event_url,
        decode_responses=False,
    )
    yield client
    await client.aclose()


def create_test_app(settings: Settings) -> Litestar:
    """Create a fresh Litestar app for testing.

    This creates new plugin instances to avoid event loop binding issues.
    CSRF is disabled for testing to simplify test setup.
    Uses in-memory stores to avoid Valkey event loop issues.

    The app creates its own SQLSpec instance that will be bound to the
    test client's event loop, avoiding asyncpg connection pool issues.

    Args:
        settings: Test settings instance with test container ports
    """
    import sys

    # Debug: print the database connection settings
    print(
        f"DEBUG: Creating test app with DB {settings.db_host}:{settings.db_port}/{settings.db_name}",
        file=sys.stderr,
    )

    from litestar import Litestar
    from litestar.channels import ChannelsPlugin
    from litestar.channels.backends.memory import MemoryChannelsBackend
    from litestar.di import Provide
    from litestar.middleware.session.server_side import ServerSideSessionConfig
    from litestar.stores.memory import MemoryStore
    from sqlspec import SQLSpec as SQLSpecClass
    from sqlspec.adapters.asyncpg import AsyncpgConfig, AsyncpgPoolConfig
    from sqlspec.extensions.litestar import SQLSpecPlugin

    from api.di import provide_valkey_client
    from api.middleware import (
        auth_middleware,
        compression_config,
        cors_config,
    )
    from routes import (
        AuthController,
        HealthController,
        MapController,
        UniverseController,
        UserController,
    )

    # Use memory backend for tests to avoid event loop issues
    test_channels_plugin = ChannelsPlugin(
        backend=MemoryChannelsBackend(history=100),
        arbitrary_channels_allowed=True,
        create_ws_route_handlers=False,
    )

    # Use in-memory stores for tests
    test_sessions_store = MemoryStore()
    test_rl_store = MemoryStore()

    # Create a test-specific session config
    test_session_config = ServerSideSessionConfig(
        key="session",
        max_age=settings.session_max_age,
    )

    # Create database config explicitly from test settings to avoid any caching issues
    # Migrations are disabled here - they're handled by the db_config fixture
    test_db_config = AsyncpgConfig(
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

    # Create a fresh SQLSpec instance for the app
    # This will create its own connection pool bound to the app's event loop
    app_sql = SQLSpecClass()
    app_sql.add_config(test_db_config)
    test_sqlspec_plugin = SQLSpecPlugin(sqlspec=app_sql)

    return Litestar(
        route_handlers=[
            AuthController,
            HealthController,
            MapController,
            UniverseController,
            UserController,
        ],
        plugins=[test_sqlspec_plugin, test_channels_plugin],
        stores={
            "sessions": test_sessions_store,
            "rate_limit": test_rl_store,
        },
        dependencies={"valkey_client": Provide(provide_valkey_client)},
        middleware=[test_session_config.middleware, auth_middleware],
        cors_config=cors_config,
        # CSRF disabled for testing - not needed for integration tests
        compression_config=compression_config,
        debug=settings.debug,
    )


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def test_app(override_settings: Settings, preseed_data: None) -> Litestar:  # noqa: ARG001
    """Create test Litestar app.

    The app creates its own SQLSpec instance that will be bound to the
    test client's event loop, avoiding asyncpg connection pool issues.
    """
    return create_test_app(override_settings)


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def test_client(test_app: Litestar) -> AsyncGenerator[AsyncTestClient]:
    """Provide AsyncTestClient for each test.

    Uses raise_server_exceptions=False to handle server errors gracefully
    and avoid event loop issues with asyncpg connection pooling.
    """
    from litestar.middleware.session.server_side import ServerSideSessionConfig

    # Use the same session config as the test app
    test_session_config = ServerSideSessionConfig(
        key="session",
        max_age=604800,
    )

    async with AsyncTestClient(
        app=test_app,
        session_config=test_session_config,
        raise_server_exceptions=False,
    ) as client:
        yield client
