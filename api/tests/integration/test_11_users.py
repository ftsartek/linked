"""User routes integration tests.

Tests for character management, session preferences, and location tracking.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from services.eve_sso import BASE_SCOPES, OPTIONAL_SCOPE_GROUPS, ScopeGroup
from tests.factories.static_data import (
    JITA_44_STATION_ID,
    JITA_44_STATION_NAME,
    JITA_SYSTEM_ID,
    TEST4_CHARACTER_ID,
    TEST4_CHARACTER_NAME,
    TEST_CHARACTER_ID,
    TEST_CHARACTER_NAME,
    TEST_STRUCTURE_ID,
    TEST_STRUCTURE_NAME,
)
from tests.fixtures.esi_mock import create_mock_access_token
from tests.integration.conftest import IntegrationTestState

# =============================================================================
# Character Listing Tests
# =============================================================================


@pytest.mark.order(1100)
async def test_list_characters(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """List all characters linked to current user."""
    response = await test_client.get("/users/characters")
    assert response.status_code == 200

    data = response.json()
    assert "characters" in data
    char_ids = [c["id"] for c in data["characters"]]
    assert test_state.character_id in char_ids


@pytest.mark.order(1101)
async def test_get_character(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Get specific character details."""
    response = await test_client.get(f"/users/characters/{test_state.character_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == test_state.character_id
    assert data["name"] == test_state.character_name
    assert "corporation_id" in data
    assert "alliance_id" in data
    assert "date_created" in data


@pytest.mark.order(1102)
async def test_get_character_not_found(test_client: AsyncClient) -> None:
    """Get non-existent character returns 404."""
    response = await test_client.get("/users/characters/999999999")
    assert response.status_code == 404


# =============================================================================
# Session Preferences Tests
# =============================================================================


@pytest.mark.order(1110)
async def test_get_session_preferences_empty(test_client: AsyncClient) -> None:
    """Get preferences with no state set."""
    response = await test_client.get("/users/preferences")
    assert response.status_code == 200

    data = response.json()
    assert "selected_map_id" in data
    assert "viewports" in data


@pytest.mark.order(1111)
async def test_update_session_preferences(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Update selected map preference."""
    assert test_state.map_id is not None

    response = await test_client.patch(
        "/users/preferences",
        json={"selected_map_id": str(test_state.map_id)},
    )
    assert response.status_code == 204


@pytest.mark.order(1112)
async def test_update_map_viewport(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Update viewport for specific map."""
    assert test_state.map_id is not None

    response = await test_client.patch(
        f"/users/preferences/maps/{test_state.map_id}/viewport",
        json={"viewport": {"x": 100.5, "y": 200.5, "zoom": 1.5}},
    )
    assert response.status_code == 204


@pytest.mark.order(1113)
async def test_get_session_preferences_with_data(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify preferences were persisted."""
    response = await test_client.get("/users/preferences")
    assert response.status_code == 200

    data = response.json()
    assert data["selected_map_id"] == str(test_state.map_id)
    assert data["viewports"] is not None

    viewport = data["viewports"].get(str(test_state.map_id))
    assert viewport is not None
    assert viewport["x"] == 100.5
    assert viewport["y"] == 200.5
    assert viewport["zoom"] == 1.5


# =============================================================================
# Character Linking Tests
# =============================================================================


@pytest.mark.order(1120)
async def test_link_character_redirect(test_client: AsyncClient) -> None:
    """Verify /users/characters/link redirects to EVE SSO."""
    response = await test_client.get("/users/characters/link", follow_redirects=False)
    assert response.status_code == 302

    location = response.headers.get("location", "")
    assert "login.eveonline.com" in location


@pytest.mark.order(1121)
async def test_link_second_character(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Link a second character to the account."""
    setup_resp = await test_client.get("/test/auth-setup", params={"linking": "true"})
    assert setup_resp.status_code == 200
    oauth_state = setup_resp.json()["state"]

    mock_code = create_mock_access_token(TEST4_CHARACTER_ID, TEST4_CHARACTER_NAME)

    response = await test_client.get(
        "/auth/callback",
        params={"code": mock_code, "state": oauth_state},
        follow_redirects=False,
    )
    assert response.status_code == 302

    # Verify second character is now linked
    list_resp = await test_client.get("/users/characters")
    assert list_resp.status_code == 200
    char_ids = [c["id"] for c in list_resp.json()["characters"]]
    assert TEST4_CHARACTER_ID in char_ids

    test_state.second_character_id = TEST4_CHARACTER_ID


# =============================================================================
# Primary Character Tests
# =============================================================================


@pytest.mark.order(1130)
async def test_set_primary_character(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Set primary character to second character."""
    assert test_state.second_character_id is not None

    response = await test_client.put(
        "/users/primary-character",
        json={"character_id": test_state.second_character_id},
    )
    assert response.status_code == 204

    me_resp = await test_client.get("/auth/me")
    assert me_resp.status_code == 200
    assert me_resp.json()["primary_character_id"] == test_state.second_character_id


@pytest.mark.order(1131)
async def test_set_primary_character_not_found(test_client: AsyncClient) -> None:
    """Set primary to non-existent character returns 404."""
    response = await test_client.put(
        "/users/primary-character",
        json={"character_id": 999999999},
    )
    assert response.status_code == 404


# =============================================================================
# Character Deletion Tests
# =============================================================================


@pytest.mark.order(1140)
async def test_cannot_delete_primary_character(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify primary character cannot be deleted."""
    assert test_state.second_character_id is not None

    response = await test_client.delete(f"/users/characters/{test_state.second_character_id}")
    assert response.status_code == 400
    assert "primary" in response.json().get("detail", "").lower()


@pytest.mark.order(1141)
async def test_delete_second_character(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Delete second (non-primary) character."""
    # Set original character back as primary so we can delete TEST4
    response = await test_client.put(
        "/users/primary-character",
        json={"character_id": test_state.character_id},
    )
    assert response.status_code == 204

    response = await test_client.delete(f"/users/characters/{test_state.second_character_id}")
    assert response.status_code == 204

    test_state.second_character_id = None


@pytest.mark.order(1142)
async def test_cannot_delete_last_character(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify last remaining character cannot be deleted."""
    response = await test_client.delete(f"/users/characters/{test_state.character_id}")
    assert response.status_code == 400
    assert "last" in response.json().get("detail", "").lower()


# =============================================================================
# Location Refresh Tests
# =============================================================================


@pytest.mark.order(1150)
async def test_relink_with_location_scope(test_client: AsyncClient) -> None:
    """Re-link character with location scope for location refresh tests."""
    setup_resp = await test_client.get(
        "/test/auth-setup",
        params={"scopes": "location", "linking": "true"},
    )
    assert setup_resp.status_code == 200
    oauth_state = setup_resp.json()["state"]

    all_scopes = [*BASE_SCOPES, *OPTIONAL_SCOPE_GROUPS[ScopeGroup.LOCATION]]
    mock_code = create_mock_access_token(TEST_CHARACTER_ID, TEST_CHARACTER_NAME, scopes=all_scopes)

    response = await test_client.get(
        "/auth/callback",
        params={"code": mock_code, "state": oauth_state},
        follow_redirects=False,
    )
    assert response.status_code == 302


@pytest.mark.order(1151)
async def test_location_refresh_success(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Location refresh returns data when scope is enabled."""
    response = await test_client.post(
        f"/users/characters/{test_state.character_id}/location/refresh",
    )
    assert response.status_code == 201

    data = response.json()
    assert data["character_id"] == test_state.character_id
    assert data["solar_system_id"] == JITA_SYSTEM_ID
    assert data["solar_system_name"] == "Jita"
    assert data["station_id"] == JITA_44_STATION_ID
    assert data["station_name"] == JITA_44_STATION_NAME
    assert data["structure_id"] == TEST_STRUCTURE_ID
    assert data["structure_name"] == TEST_STRUCTURE_NAME
    assert "online" in data
    assert "ship_type_id" in data


@pytest.mark.order(1152)
async def test_location_refresh_not_found(test_client: AsyncClient) -> None:
    """Location refresh for non-existent character returns 404."""
    response = await test_client.post("/users/characters/999999999/location/refresh")
    assert response.status_code == 404


# =============================================================================
# Unauthenticated Access Tests
# =============================================================================


@pytest.mark.order(1160)
async def test_unauthenticated_list_characters(unauthenticated_client: AsyncClient) -> None:
    """Verify 401 when listing characters without authentication."""
    response = await unauthenticated_client.get("/users/characters")
    assert response.status_code == 401


@pytest.mark.order(1161)
async def test_unauthenticated_preferences(unauthenticated_client: AsyncClient) -> None:
    """Verify 401 when accessing preferences without authentication."""
    response = await unauthenticated_client.get("/users/preferences")
    assert response.status_code == 401
