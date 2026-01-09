"""Integration test fixtures with shared state across sequential tests."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
import pytest_asyncio
from litestar.testing import AsyncTestClient

if TYPE_CHECKING:
    from sqlspec import SQLSpec
    from sqlspec.adapters.asyncpg.driver import AsyncpgDriver
    from valkey.asyncio import Valkey

from tests.factories.static_data import TEST_CHARACTER_ID, TEST_CHARACTER_NAME
from tests.fixtures.events import EventCollector


@dataclass
class TestState:
    """Shared state across sequential integration tests.

    This allows tests to build upon each other in a logical sequence:
    1. Create user/map
    2. Search for systems
    3. Create nodes
    4. Create links
    5. Update nodes/links
    6. Test lifecycle
    7. Test soft delete
    8. Test cleanup
    """

    user_id: UUID | None = None
    character_id: int | None = None
    character_name: str = TEST_CHARACTER_NAME
    map_id: UUID | None = None
    node_ids: list[UUID] = field(default_factory=list)
    link_ids: list[UUID] = field(default_factory=list)
    k162_wormhole_id: int | None = None
    lifecycle_link_id: UUID | None = None


# Use session scope to share state across all test modules
@pytest.fixture(scope="session")
def test_state() -> TestState:
    """Shared test state for sequential tests."""
    return TestState()


@pytest_asyncio.fixture(loop_scope="session")
async def db_session(db_engine: SQLSpec, db: Any) -> AsyncGenerator[AsyncpgDriver]:
    """Function-scoped database session for integration tests."""
    async with db_engine.provide_session(db) as session:
        yield session


async def set_auth(client: AsyncTestClient, test_state: TestState) -> None:
    """Helper to set up authentication session data on test client.

    This must be called before making authenticated requests.
    """
    if test_state.user_id is None:
        raise ValueError("test_state.user_id must be set before authenticating")

    await client.set_session_data(
        {
            "user_id": str(test_state.user_id),
            "character_id": test_state.character_id or TEST_CHARACTER_ID,
            "character_name": test_state.character_name,
        }
    )


@pytest_asyncio.fixture
async def event_collector(
    valkey_client: Valkey,
    test_state: TestState,
) -> AsyncGenerator[EventCollector | None]:
    """Provides event collector for SSE verification.

    Subscribes to the map's event channel and collects published events
    so tests can verify the correct events are emitted.

    Returns None if map_id is not set yet (for tests that run before map creation).
    """
    if test_state.map_id is None:
        yield None
        return

    collector = EventCollector(valkey_client, test_state.map_id)
    await collector.start()
    yield collector
    await collector.stop()
