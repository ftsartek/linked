"""Authentication integration tests.

These tests verify that the authentication flow works correctly with mocked ESI/SSO.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.factories.static_data import TEST_CHARACTER_ID, TEST_CHARACTER_NAME
from tests.integration.conftest import IntegrationTestState, authenticate_via_callback


@pytest.mark.order(0)
async def test_unauthenticated_me_returns_401(test_client: AsyncClient) -> None:
    """Verify /auth/me returns 401 when not authenticated."""
    response = await test_client.get("/auth/me")
    assert response.status_code == 401


@pytest.mark.order(1)
async def test_authenticate_via_callback(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Test authentication via mocked SSO callback flow.

    This creates a new user and authenticates the test client.
    Subsequent tests can rely on this authentication.

    Note: No mock_eve_services fixture needed - MockEveSSOService and
    MockESIClient are injected via DI in the test app.
    """
    await authenticate_via_callback(
        client=test_client,
        test_state=test_state,
    )

    # Verify test_state was updated
    assert test_state.user_id is not None
    assert test_state.character_id == TEST_CHARACTER_ID
    assert test_state.character_name == TEST_CHARACTER_NAME


@pytest.mark.order(2)
async def test_authenticated_me_returns_user_info(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify /auth/me returns user info when authenticated."""
    response = await test_client.get("/auth/me")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == str(test_state.user_id)
    assert len(data["characters"]) >= 1

    # Find our test character in the list
    character = next(
        (c for c in data["characters"] if c["id"] == TEST_CHARACTER_ID),
        None,
    )
    assert character is not None
    assert character["name"] == TEST_CHARACTER_NAME
