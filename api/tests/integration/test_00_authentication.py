"""Authentication integration tests.

These tests verify that the authentication flow works correctly with mocked ESI/SSO.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from services.eve_sso import BASE_SCOPES, OPTIONAL_SCOPE_GROUPS, ScopeGroup
from tests.factories.static_data import TEST_CHARACTER_ID, TEST_CHARACTER_NAME
from tests.fixtures.esi_mock import create_mock_access_token
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


@pytest.mark.order(3)
async def test_me_returns_empty_scope_groups_for_base_auth(
    test_client: AsyncClient,
) -> None:
    """Verify /auth/me returns empty scope_groups for character with base scopes only."""
    response = await test_client.get("/auth/me")
    assert response.status_code == 200

    data = response.json()
    character = next(
        (c for c in data["characters"] if c["id"] == TEST_CHARACTER_ID),
        None,
    )
    assert character is not None
    assert "scope_groups" in character
    assert character["scope_groups"] == []


@pytest.mark.order(4)
def test_build_scopes_returns_base_scopes_by_default() -> None:
    """Verify build_scopes returns base scopes when no groups specified."""
    from services.eve_sso import build_scopes

    scopes = build_scopes()
    for base_scope in BASE_SCOPES:
        assert base_scope in scopes


@pytest.mark.order(5)
def test_build_scopes_includes_location_scopes_when_requested() -> None:
    """Verify build_scopes includes location scopes when location group is requested."""
    from services.eve_sso import build_scopes

    scopes = build_scopes([ScopeGroup.LOCATION])

    # Should include base scopes
    for base_scope in BASE_SCOPES:
        assert base_scope in scopes

    # Should include location scopes
    location_scopes = OPTIONAL_SCOPE_GROUPS[ScopeGroup.LOCATION]
    for scope in location_scopes:
        assert scope in scopes


@pytest.mark.order(6)
async def test_link_redirect_includes_location_scopes_when_requested(
    test_client: AsyncClient,
) -> None:
    """Verify /auth/link includes location scopes when ?scopes=location is passed."""
    response = await test_client.get("/auth/link", params={"scopes": "location"}, follow_redirects=False)
    assert response.status_code == 302

    location = response.headers.get("location", "")
    assert "login.eveonline.com" in location

    # Check that location scopes are in the URL
    location_scopes = OPTIONAL_SCOPE_GROUPS[ScopeGroup.LOCATION]
    for scope in location_scopes:
        assert scope.replace(".", "%2E") in location or scope in location


@pytest.mark.order(7)
async def test_reauth_with_location_scopes_updates_character(
    test_client: AsyncClient,
) -> None:
    """Verify re-authenticating with location scopes updates the character's scope_groups."""
    # Set up auth with location scopes
    setup_resp = await test_client.get("/test/auth-setup", params={"scopes": "location", "linking": "true"})
    assert setup_resp.status_code == 200
    oauth_state = setup_resp.json()["state"]

    # Create mock token with location scopes
    all_scopes = [
        *BASE_SCOPES,
        *OPTIONAL_SCOPE_GROUPS[ScopeGroup.LOCATION],
    ]
    mock_code = create_mock_access_token(TEST_CHARACTER_ID, TEST_CHARACTER_NAME, scopes=all_scopes)

    # Hit callback - this should update the existing character's scopes
    response = await test_client.get(
        "/auth/callback",
        params={"code": mock_code, "state": oauth_state},
        follow_redirects=False,
    )
    assert response.status_code == 302

    # Verify /auth/me now shows location scope group
    me_resp = await test_client.get("/auth/me")
    assert me_resp.status_code == 200

    data = me_resp.json()
    character = next(
        (c for c in data["characters"] if c["id"] == TEST_CHARACTER_ID),
        None,
    )
    assert character is not None
    assert "scope_groups" in character
    assert "location" in character["scope_groups"]
