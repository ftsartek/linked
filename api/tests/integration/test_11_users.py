"""User routes integration tests.

Tests for character management, session preferences, and location tracking.
"""

from __future__ import annotations

import asyncio

import pytest
from httpx import AsyncClient

from routes.maps.events import EventType
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
from tests.fixtures.events import (
    assert_event_published,
    collect_sse_events,
    find_events_of_type,
)
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
# Location Propagation Tests
# =============================================================================


@pytest.mark.order(1153)
async def test_ensure_jita_node_for_location_tests(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Ensure test map has a Jita node for location propagation tests.

    The Jita node should already exist from test_02_nodes.py, but we verify
    it here to ensure location events can be emitted for characters in Jita.
    """
    assert test_state.map_id is not None

    # Get map detail and verify Jita node exists
    response = await test_client.get(f"/maps/{test_state.map_id}")
    assert response.status_code == 200

    data = response.json()
    nodes = data.get("nodes", [])
    jita_node = next((n for n in nodes if n["system_id"] == JITA_SYSTEM_ID), None)

    assert jita_node is not None, "Jita node should exist from test_02_nodes.py"


@pytest.mark.order(1154)
async def test_link_second_character_with_location_scope(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Link a second character with location scope for deletion testing.

    This character will be deleted in subsequent tests to verify
    CHARACTER_LEFT events are emitted correctly.
    """
    # Set up auth with location scopes for linking
    setup_resp = await test_client.get(
        "/test/auth-setup",
        params={"scopes": "location", "linking": "true"},
    )
    assert setup_resp.status_code == 200
    oauth_state = setup_resp.json()["state"]

    # Create mock token with location scopes
    all_scopes = [*BASE_SCOPES, *OPTIONAL_SCOPE_GROUPS[ScopeGroup.LOCATION]]
    mock_code = create_mock_access_token(TEST4_CHARACTER_ID, TEST4_CHARACTER_NAME, scopes=all_scopes)

    # Complete auth callback to link character
    response = await test_client.get(
        "/auth/callback",
        params={"code": mock_code, "state": oauth_state},
        follow_redirects=False,
    )
    assert response.status_code == 302

    # Verify character is linked
    list_resp = await test_client.get("/users/characters")
    assert list_resp.status_code == 200
    char_ids = [c["id"] for c in list_resp.json()["characters"]]
    assert TEST4_CHARACTER_ID in char_ids

    # Store for later tests
    test_state.second_character_id = TEST4_CHARACTER_ID


@pytest.mark.order(1155)
async def test_refresh_second_character_location(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Refresh location for second character to populate cache.

    This ensures the character has cached location data in Jita,
    which is required for CHARACTER_LEFT events on deletion.
    Also verifies the new corporation_name and alliance_name fields.
    """
    assert test_state.second_character_id is not None

    response = await test_client.post(
        f"/users/characters/{test_state.second_character_id}/location/refresh",
    )
    assert response.status_code == 201

    data = response.json()
    assert data["character_id"] == test_state.second_character_id
    assert data["solar_system_id"] == JITA_SYSTEM_ID
    # Verify new fields are present
    assert "corporation_name" in data
    assert "alliance_name" in data


@pytest.mark.order(1156)
async def test_character_deletion_emits_character_left_event(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify CHARACTER_LEFT event is emitted when character with cached location is deleted.

    The second character was linked with location scope and had its location
    refreshed (cached in Jita). Deleting it should emit CHARACTER_LEFT to
    the map that has a Jita node.
    """
    assert test_state.map_id is not None
    assert test_state.second_character_id is not None

    # Get the current last event_id to filter out history when we connect to SSE
    drain_events = await collect_sse_events(test_client, test_state.map_id, timeout=0.5, max_events=100)
    last_event_id = drain_events[-1].event_id if drain_events else "0"

    # Start SSE collection before deletion, filtering out old events
    connected = asyncio.Event()
    collect_task = asyncio.create_task(
        collect_sse_events(
            test_client,
            test_state.map_id,
            timeout=2.0,
            max_events=50,
            connected_event=connected,
            last_event_id=last_event_id,
        )
    )
    await asyncio.wait_for(connected.wait(), timeout=1.0)

    # Delete the character
    response = await test_client.delete(f"/users/characters/{test_state.second_character_id}")
    assert response.status_code == 204

    # Collect and verify CHARACTER_LEFT event
    events = await collect_task
    event = assert_event_published(
        events,
        EventType.CHARACTER_LEFT,
        character_name=TEST4_CHARACTER_NAME,
    )

    # Verify event data includes corporation_name and alliance_name
    assert "corporation_name" in event.data
    assert "alliance_name" in event.data
    assert "node_id" in event.data

    # Clear second_character_id since it's deleted
    test_state.second_character_id = None


@pytest.mark.order(1157)
async def test_character_deletion_without_cached_location_no_events(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify character deletion without cached location doesn't emit events.

    Link a character WITHOUT location scope, then delete it. No CHARACTER_LEFT
    event should be emitted since there's no cached location data.
    """
    assert test_state.map_id is not None

    # Link character WITHOUT location scope (base scopes only)
    setup_resp = await test_client.get(
        "/test/auth-setup",
        params={"linking": "true"},  # No scopes param = base scopes only
    )
    assert setup_resp.status_code == 200
    oauth_state = setup_resp.json()["state"]

    mock_code = create_mock_access_token(TEST4_CHARACTER_ID, TEST4_CHARACTER_NAME)

    response = await test_client.get(
        "/auth/callback",
        params={"code": mock_code, "state": oauth_state},
        follow_redirects=False,
    )
    assert response.status_code == 302

    # Get the current last event_id to filter out history when we connect to SSE
    drain_events = await collect_sse_events(test_client, test_state.map_id, timeout=0.5, max_events=100)
    last_event_id = drain_events[-1].event_id if drain_events else "0"

    # Start SSE collection, filtering out old events
    connected = asyncio.Event()
    collect_task = asyncio.create_task(
        collect_sse_events(
            test_client,
            test_state.map_id,
            timeout=1.5,
            max_events=50,
            connected_event=connected,
            last_event_id=last_event_id,
        )
    )
    await asyncio.wait_for(connected.wait(), timeout=1.0)

    # Delete the character (no cached location, so no events expected)
    response = await test_client.delete(f"/users/characters/{TEST4_CHARACTER_ID}")
    assert response.status_code == 204

    # Verify no CHARACTER_LEFT events were emitted
    events = await collect_task
    character_left_events = find_events_of_type(events, EventType.CHARACTER_LEFT)
    assert len(character_left_events) == 0, f"Expected no CHARACTER_LEFT events, got {len(character_left_events)}"


@pytest.mark.order(1158)
async def test_scope_removal_clears_cache_keys(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify re-authorizing without location scope clears location cache.

    1. Character already has location scope (from test_relink_with_location_scope)
    2. Refresh location to populate cache
    3. Re-authorize WITHOUT location scope
    4. Verify location refresh now returns 403 (no scope)

    Note: The _clear_location_cache in auth service does NOT emit SSE events
    due to circular dependency concerns. The character simply disappears from
    nodes on next map load.
    """
    # First, ensure primary character has location scope and cached location
    # (This should already be the case from test order 1150-1151)

    # Verify location works before scope removal
    refresh_resp = await test_client.post(
        f"/users/characters/{test_state.character_id}/location/refresh",
    )
    assert refresh_resp.status_code == 201
    assert refresh_resp.json()["solar_system_id"] == JITA_SYSTEM_ID

    # Re-authorize WITHOUT location scope (linking=true to update existing char)
    setup_resp = await test_client.get(
        "/test/auth-setup",
        params={"linking": "true"},  # No scopes = base scopes only
    )
    assert setup_resp.status_code == 200
    oauth_state = setup_resp.json()["state"]

    # Create mock token with base scopes only (no location)
    mock_code = create_mock_access_token(TEST_CHARACTER_ID, TEST_CHARACTER_NAME)

    response = await test_client.get(
        "/auth/callback",
        params={"code": mock_code, "state": oauth_state},
        follow_redirects=False,
    )
    assert response.status_code == 302

    # Verify location refresh now returns 403 (no scope)
    refresh_resp = await test_client.post(
        f"/users/characters/{test_state.character_id}/location/refresh",
    )
    assert refresh_resp.status_code == 403

    data = refresh_resp.json()
    assert data["error"] == "no_scope"


@pytest.mark.order(1159)
async def test_scope_removal_no_sse_events(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify scope removal clears cache but does NOT emit CHARACTER_LEFT events.

    Due to circular dependency concerns, _clear_location_cache in the auth
    service does not emit SSE events. This is by design - the character will
    disappear from nodes on next map load.
    """
    assert test_state.map_id is not None

    # First, re-add location scope to the character
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

    # Refresh location to populate cache
    refresh_resp = await test_client.post(
        f"/users/characters/{test_state.character_id}/location/refresh",
    )
    assert refresh_resp.status_code == 201

    # Get the current last event_id to filter out history when we connect to SSE
    drain_events = await collect_sse_events(test_client, test_state.map_id, timeout=0.5, max_events=100)
    last_event_id = drain_events[-1].event_id if drain_events else "0"

    # Start SSE collection, filtering out old events
    connected = asyncio.Event()
    collect_task = asyncio.create_task(
        collect_sse_events(
            test_client,
            test_state.map_id,
            timeout=1.5,
            max_events=50,
            connected_event=connected,
            last_event_id=last_event_id,
        )
    )
    await asyncio.wait_for(connected.wait(), timeout=1.0)

    # Re-authorize WITHOUT location scope
    setup_resp = await test_client.get(
        "/test/auth-setup",
        params={"linking": "true"},
    )
    assert setup_resp.status_code == 200
    oauth_state = setup_resp.json()["state"]

    mock_code = create_mock_access_token(TEST_CHARACTER_ID, TEST_CHARACTER_NAME)

    response = await test_client.get(
        "/auth/callback",
        params={"code": mock_code, "state": oauth_state},
        follow_redirects=False,
    )
    assert response.status_code == 302

    # Verify NO CHARACTER_LEFT events were emitted
    events = await collect_task
    character_left_events = find_events_of_type(events, EventType.CHARACTER_LEFT)
    assert len(character_left_events) == 0, "Scope removal should NOT emit CHARACTER_LEFT events"


@pytest.mark.order(1160)
async def test_restore_location_scope(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Restore location scope for primary character.

    This ensures the character has location scope for any subsequent
    tests that may depend on it.
    """
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

    # Verify location refresh works
    refresh_resp = await test_client.post(
        f"/users/characters/{test_state.character_id}/location/refresh",
    )
    assert refresh_resp.status_code == 201


# =============================================================================
# Unauthenticated Access Tests
# =============================================================================


@pytest.mark.order(1180)
async def test_unauthenticated_list_characters(unauthenticated_client: AsyncClient) -> None:
    """Verify 401 when listing characters without authentication."""
    response = await unauthenticated_client.get("/users/characters")
    assert response.status_code == 401


@pytest.mark.order(1181)
async def test_unauthenticated_preferences(unauthenticated_client: AsyncClient) -> None:
    """Verify 401 when accessing preferences without authentication."""
    response = await unauthenticated_client.get("/users/preferences")
    assert response.status_code == 401
