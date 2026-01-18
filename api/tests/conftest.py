"""Root test configuration with session-scoped Docker containers and fixtures."""

from __future__ import annotations

import os
import socket
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from httpx import AsyncClient
from litestar.testing import subprocess_async_client
from sqlspec import SQLSpec
from sqlspec.adapters.asyncpg import AsyncpgConfig, AsyncpgPoolConfig

from config import get_settings
from tests.fixtures.preseed import preseed_test_data

if TYPE_CHECKING:
    pass


# Set CONFIG_FILE before any settings are loaded
os.environ["CONFIG_FILE"] = str(Path(__file__).parent / "config.test.yaml")

# Register fixture modules for pytest discovery
pytest_plugins = [
    "tests.fixtures.esi_mock",
]


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest markers."""
    config.addinivalue_line("markers", "order: specify test execution order")


# =============================================================================
# pytest-docker configuration
# =============================================================================


@pytest.fixture(scope="session")
def docker_compose_file() -> Path:
    """Path to docker-compose file for test containers."""
    return Path(__file__).parent / "docker-compose.yml"


@pytest.fixture(scope="session")
def docker_compose_project_name() -> str:
    """Unique project name to avoid conflicts."""
    return "linked_test"


# =============================================================================
# Service readiness utilities
# =============================================================================


def is_responsive(host: str, port: int, timeout: float = 5.0) -> bool:
    """Check if a service is responsive via TCP connection."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, TimeoutError):
        return False


def wait_until_responsive(
    check: Callable,
    timeout: int = 30,
    pause: float = 0.5,
) -> None:
    """Wait until check() returns True or timeout expires."""
    import time

    start = time.time()
    while not check():
        if time.time() - start > timeout:
            raise TimeoutError(f"Service not responsive after {timeout} seconds")
        time.sleep(pause)


# =============================================================================
# Service readiness fixtures
# =============================================================================


@pytest.fixture(scope="session")
def postgres_responsive() -> str:
    """Wait for PostgreSQL to be responsive and return connection URI."""
    wait_until_responsive(
        timeout=30,
        pause=0.2,
        check=lambda: is_responsive(get_settings().postgres.host, get_settings().postgres.port),
    )
    return get_settings().postgres.uri


@pytest.fixture(scope="session")
def valkey_responsive() -> str:
    """Wait for Valkey to be responsive and return connection URL."""
    wait_until_responsive(
        timeout=30,
        pause=0.2,
        check=lambda: is_responsive(get_settings().valkey.host, get_settings().valkey.port),
    )
    return get_settings().valkey.session_url


# =============================================================================
# Database migration fixture
# =============================================================================


@pytest.fixture(scope="session")
def _run_migrations(
    docker_services: Any,  # noqa: ARG001
    postgres_responsive: str,  # noqa: ARG001 - Ensures DB is ready
    valkey_responsive: str,  # noqa: ARG001 - Ensures Valkey is ready
) -> None:
    """Run migrations before app startup.

    Uses asyncio.run() to create a temporary event loop for migration,
    avoiding the loop mismatch issue. Creates its own SQLSpec instance
    and config so the main app's SQLSpec remains unaffected.
    """
    import asyncio

    async def run() -> None:
        migration_config = AsyncpgConfig(
            connection_config=AsyncpgPoolConfig(
                dsn=postgres_responsive,
                min_size=1,
                max_size=2,
                ssl=get_settings().postgres.ssl,
            ),
            migration_config={
                "enabled": True,
                "script_location": Path(__file__).parent.parent / "migrations",
                "version_table_name": "ddl_migrations",
            },
        )

        sql = SQLSpec()
        db = sql.add_config(migration_config)
        await db.migrate_up("head")

        # Preseed test data
        async with db.provide_session() as session:
            await preseed_test_data(session)

        await sql.close_pool(db)

    asyncio.run(run())


# =============================================================================
# Test client fixture
# =============================================================================


@pytest.fixture(scope="session")
async def test_client(_run_migrations: None) -> AsyncIterator[AsyncClient]:
    workdir = Path(__file__).parent.parent
    async with subprocess_async_client(workdir=workdir, app="tests.factories.app:app") as client:
        yield client
