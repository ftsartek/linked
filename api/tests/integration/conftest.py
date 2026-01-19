"""Integration test fixtures with shared state across sequential tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

import pytest
from httpx import AsyncClient

from tests.factories.static_data import TEST_CHARACTER_ID, TEST_CHARACTER_NAME
from tests.fixtures.esi_mock import create_mock_access_token


@dataclass
class IntegrationTestState:
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
    signature_ids: list[UUID] = field(default_factory=list)
    deleted_signature_ids: list[UUID] = field(default_factory=list)
    note_ids: list[UUID] = field(default_factory=list)
    k162_wormhole_id: int | None = None
    lifecycle_link_id: UUID | None = None


# Use session scope to share state across all test modules
@pytest.fixture(scope="session")
def test_state() -> IntegrationTestState:
    """Shared test state for sequential tests."""
    return IntegrationTestState()


async def authenticate_via_callback(
    client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Authenticate by going through the mocked SSO callback flow.

    This tests the full auth flow with mocked ESI/SSO services.
    After this call, the client session is authenticated and test_state
    is updated with the user_id and character_id.

    Works with subprocess_async_client by using HTTP endpoints instead of
    direct session manipulation.

    Args:
        client: The httpx AsyncClient to authenticate
        test_state: Test state to update with auth info
    """
    # Step 1: Set up oauth state via test endpoint
    # This simulates what /auth/login does (setting oauth_state in session)
    setup_resp = await client.get("/test/auth-setup")
    assert setup_resp.status_code == 200, f"Auth setup failed: {setup_resp.text}"
    oauth_state = setup_resp.json()["state"]

    # Step 2: Create mock auth code (which MockEveSSOService will decode)
    mock_code = create_mock_access_token(TEST_CHARACTER_ID, TEST_CHARACTER_NAME)

    # Step 3: Hit callback with mock code and state
    # Cookies persist automatically in httpx client
    response = await client.get(
        "/auth/callback",
        params={"code": mock_code, "state": oauth_state},
        follow_redirects=False,
    )

    # Should redirect to frontend after successful auth
    assert response.status_code == 302, f"Auth callback failed: {response.text}"

    # Step 4: Get user info from /auth/me to populate test_state
    me_resp = await client.get("/auth/me")
    assert me_resp.status_code == 200, f"Get user info failed: {me_resp.text}"
    data = me_resp.json()

    test_state.user_id = UUID(data["id"])

    # Find the test character in the list
    char = next(
        (c for c in data["characters"] if c["id"] == TEST_CHARACTER_ID),
        None,
    )
    assert char is not None, f"Test character not found in user characters: {data}"
    test_state.character_id = char["id"]
    test_state.character_name = char["name"]
