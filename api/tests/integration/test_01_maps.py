"""Map integration tests.

These tests verify map creation, listing, sharing, and public map functionality.
Tests run in order after authentication tests (test_00_authentication.py).
"""

from __future__ import annotations

import asyncio
from uuid import UUID

import pytest
from httpx import AsyncClient

from routes.maps.events import EventType
from tests.factories.static_data import (
    ALLIANCE_SHARED_MAP_ID,
    ALLIANCE_SHARED_MAP_NAME,
    CORP_SHARED_MAP_ID,
    CORP_SHARED_MAP_NAME,
    PUBLIC_MAP_DESCRIPTION,
    PUBLIC_MAP_ID,
    PUBLIC_MAP_NAME,
    TEST2_ALLIANCE_ID,
    TEST2_CHARACTER_ID,
    TEST2_CORPORATION_ID,
)
from tests.fixtures.events import assert_event_published, collect_sse_events
from tests.integration.conftest import IntegrationTestState

# =============================================================================
# Map Creation Tests
# =============================================================================


@pytest.mark.order(10)
async def test_create_map_requires_name(test_client: AsyncClient) -> None:
    """Verify map creation requires a name field."""
    # This test uses the authenticated session to verify validation
    response = await test_client.post(
        "/maps/",
        json={},  # Missing required 'name' field
    )
    assert response.status_code == 400


@pytest.mark.order(11)
async def test_create_map_minimal(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Create a map with minimal required fields."""
    response = await test_client.post(
        "/maps/",
        json={"name": "My Test Map"},
    )
    assert response.status_code == 201, f"Failed to create map: {response.text}"

    data = response.json()
    assert data["name"] == "My Test Map"
    assert data["owner_id"] == str(test_state.user_id)
    assert data["is_public"] is False
    assert data["edit_access"] is True  # Owner always has edit access
    assert "id" in data

    # Store map ID for later tests
    test_state.map_id = UUID(data["id"])


@pytest.mark.order(12)
async def test_create_map_with_all_options(
    test_client: AsyncClient,
    test_state: IntegrationTestState,  # noqa: ARG001
) -> None:
    """Create a map with all optional fields specified."""
    response = await test_client.post(
        "/maps/",
        json={
            "name": "Full Options Map",
            "description": "A map with all options set",
            "is_public": False,
            "public_read_only": True,
            "edge_type": "default",
            "rankdir": "LR",
            "auto_layout": True,
            "node_sep": 80,
            "rank_sep": 100,
        },
    )
    assert response.status_code == 201, f"Failed to create map: {response.text}"

    data = response.json()
    assert data["name"] == "Full Options Map"
    assert data["description"] == "A map with all options set"
    assert data["rankdir"] == "LR"
    assert data["auto_layout"] is True
    assert data["node_sep"] == 80
    assert data["rank_sep"] == 100


@pytest.mark.order(13)
async def test_create_map_validation_node_sep(test_client: AsyncClient) -> None:
    """Verify map creation validates node_sep field."""
    # Invalid node_sep (not multiple of 20)
    response = await test_client.post(
        "/maps/",
        json={"name": "Bad Map", "node_sep": 55},
    )
    assert response.status_code == 400


# =============================================================================
# Map Listing Tests - Owned Maps
# =============================================================================


@pytest.mark.order(20)
async def test_list_owned_maps(
    test_client: AsyncClient,
    test_state: IntegrationTestState,  # noqa: ARG001
) -> None:
    """List maps owned by the current user."""
    response = await test_client.get("/maps/owned")
    assert response.status_code == 200

    data = response.json()
    assert "maps" in data
    maps = data["maps"]

    # Should include the maps we created
    map_names = [m["name"] for m in maps]
    assert "My Test Map" in map_names
    assert "Full Options Map" in map_names

    # All maps should show edit_access = True (owner)
    for m in maps:
        assert m["edit_access"] is True


# =============================================================================
# Map Listing Tests - Corp/Alliance Shared Maps
# =============================================================================


@pytest.mark.order(30)
async def test_list_corporation_maps(test_client: AsyncClient) -> None:
    """List maps shared with user's corporation."""
    response = await test_client.get("/maps/corporation")
    assert response.status_code == 200

    data = response.json()
    assert "maps" in data
    maps = data["maps"]

    # Should include the corp-shared map from preseed
    map_ids = [m["id"] for m in maps]
    assert CORP_SHARED_MAP_ID in map_ids

    # Find the corp shared map and verify access
    corp_map = next(m for m in maps if m["id"] == CORP_SHARED_MAP_ID)
    assert corp_map["name"] == CORP_SHARED_MAP_NAME
    assert corp_map["edit_access"] is True  # Shared with read_only=false


@pytest.mark.order(31)
async def test_list_alliance_maps(test_client: AsyncClient) -> None:
    """List maps shared with user's alliance."""
    response = await test_client.get("/maps/alliance")
    assert response.status_code == 200

    data = response.json()
    assert "maps" in data
    maps = data["maps"]

    # Should include the alliance-shared map from preseed
    map_ids = [m["id"] for m in maps]
    assert ALLIANCE_SHARED_MAP_ID in map_ids

    # Find the alliance shared map and verify access
    alliance_map = next(m for m in maps if m["id"] == ALLIANCE_SHARED_MAP_ID)
    assert alliance_map["name"] == ALLIANCE_SHARED_MAP_NAME
    assert alliance_map["edit_access"] is False  # Shared with read_only=true


@pytest.mark.order(32)
async def test_can_load_corp_shared_map(test_client: AsyncClient) -> None:
    """Verify user can load a corp-shared map."""
    response = await test_client.get(f"/maps/{CORP_SHARED_MAP_ID}")
    assert response.status_code == 200

    data = response.json()
    assert data["map"]["id"] == CORP_SHARED_MAP_ID
    assert data["map"]["name"] == CORP_SHARED_MAP_NAME
    assert "nodes" in data
    assert "links" in data


@pytest.mark.order(33)
async def test_can_load_alliance_shared_map(test_client: AsyncClient) -> None:
    """Verify user can load an alliance-shared map."""
    response = await test_client.get(f"/maps/{ALLIANCE_SHARED_MAP_ID}")
    assert response.status_code == 200

    data = response.json()
    assert data["map"]["id"] == ALLIANCE_SHARED_MAP_ID
    assert data["map"]["name"] == ALLIANCE_SHARED_MAP_NAME


# =============================================================================
# Public Map Tests
# =============================================================================


@pytest.mark.order(40)
async def test_list_public_maps(test_client: AsyncClient) -> None:
    """List available public maps."""
    response = await test_client.get("/maps/public")
    assert response.status_code == 200

    data = response.json()
    assert "maps" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data

    # Public map from preseed should be listed
    map_ids = [m["id"] for m in data["maps"]]
    assert PUBLIC_MAP_ID in map_ids


@pytest.mark.order(41)
async def test_search_public_maps(test_client: AsyncClient) -> None:
    """Search for public maps by name/description."""
    # Search for the public map by name
    response = await test_client.get("/maps/public/search", params={"q": "Atlas"})
    assert response.status_code == 200

    data = response.json()
    assert "maps" in data
    map_names = [m["name"] for m in data["maps"]]
    assert PUBLIC_MAP_NAME in map_names

    # Search by description keyword
    response = await test_client.get("/maps/public/search", params={"q": "explorers"})
    assert response.status_code == 200

    data = response.json()
    map_ids = [m["id"] for m in data["maps"]]
    assert PUBLIC_MAP_ID in map_ids


@pytest.mark.order(42)
async def test_search_public_maps_no_results(test_client: AsyncClient) -> None:
    """Search for public maps with no matching results."""
    response = await test_client.get(
        "/maps/public/search",
        params={"q": "nonexistent_xyz_map_12345"},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["maps"] == []
    assert data["total"] == 0


@pytest.mark.order(43)
async def test_can_access_public_map_directly(test_client: AsyncClient) -> None:
    """Verify user can load public map directly without subscription.

    Public maps are accessible to all authenticated users - subscription
    is just for tracking in 'subscribed maps' list.
    """
    response = await test_client.get(f"/maps/{PUBLIC_MAP_ID}")
    assert response.status_code == 200

    data = response.json()
    assert data["map"]["id"] == PUBLIC_MAP_ID
    assert data["map"]["name"] == PUBLIC_MAP_NAME
    assert data["map"]["description"] == PUBLIC_MAP_DESCRIPTION


@pytest.mark.order(44)
async def test_subscribe_to_public_map(test_client: AsyncClient) -> None:
    """Subscribe to a public map to track it in subscribed list."""
    response = await test_client.post(f"/maps/{PUBLIC_MAP_ID}/subscribe")
    assert response.status_code == 201  # Created

    data = response.json()
    assert data["map_id"] == PUBLIC_MAP_ID
    assert data["subscribed"] is True


@pytest.mark.order(45)
async def test_list_subscribed_maps(test_client: AsyncClient) -> None:
    """List maps the user has subscribed to."""
    response = await test_client.get("/maps/subscribed")
    assert response.status_code == 200

    data = response.json()
    assert "maps" in data

    # Should include our subscribed public map
    map_ids = [m["id"] for m in data["maps"]]
    assert PUBLIC_MAP_ID in map_ids

    # Public map should be read-only
    public_map = next(m for m in data["maps"] if m["id"] == PUBLIC_MAP_ID)
    assert public_map["name"] == PUBLIC_MAP_NAME
    assert public_map["edit_access"] is False  # public_read_only=true


@pytest.mark.order(46)
async def test_unsubscribe_from_public_map(test_client: AsyncClient) -> None:
    """Unsubscribe from a public map."""
    response = await test_client.delete(f"/maps/{PUBLIC_MAP_ID}/subscribe")
    assert response.status_code == 200


@pytest.mark.order(47)
async def test_public_map_not_in_subscribed_after_unsubscribe(test_client: AsyncClient) -> None:
    """Verify unsubscribed public map is not in subscribed list."""
    response = await test_client.get("/maps/subscribed")
    assert response.status_code == 200

    data = response.json()
    map_ids = [m["id"] for m in data["maps"]]
    assert PUBLIC_MAP_ID not in map_ids


@pytest.mark.order(48)
async def test_can_still_access_public_map_after_unsubscribe(test_client: AsyncClient) -> None:
    """Verify public map is still accessible after unsubscribing.

    Unsubscribing only removes from 'subscribed' list, doesn't block access.
    """
    response = await test_client.get(f"/maps/{PUBLIC_MAP_ID}")
    assert response.status_code == 200

    data = response.json()
    assert data["map"]["id"] == PUBLIC_MAP_ID


# =============================================================================
# Map Update Tests
# =============================================================================


@pytest.mark.order(50)
async def test_update_owned_map(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Update a map owned by the user."""
    response = await test_client.patch(
        f"/maps/{test_state.map_id}",
        json={
            "name": "My Updated Map",
            "description": "Updated description",
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert data["name"] == "My Updated Map"
    assert data["description"] == "Updated description"


@pytest.mark.order(51)
async def test_cannot_update_corp_shared_map_as_non_owner(test_client: AsyncClient) -> None:
    """Verify non-owner cannot update map settings even with write access."""
    response = await test_client.patch(
        f"/maps/{CORP_SHARED_MAP_ID}",
        json={"name": "Hacked Map Name"},
    )
    # Should fail - only owner can update map settings
    # App returns 401 NotAuthorizedException for permission errors
    assert response.status_code == 401


# =============================================================================
# Map Access Management Tests
# =============================================================================


@pytest.mark.order(60)
async def test_get_map_access(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Get access list for an owned map."""
    response = await test_client.get(f"/maps/{test_state.map_id}/access")
    assert response.status_code == 200

    data = response.json()
    assert "characters" in data
    assert "corporations" in data
    assert "alliances" in data

    # Initially should be empty (no shares yet)
    assert data["characters"] == []
    assert data["corporations"] == []
    assert data["alliances"] == []


@pytest.mark.order(61)
async def test_cannot_get_access_for_unowned_map(test_client: AsyncClient) -> None:
    """Verify non-owner cannot view access list."""
    response = await test_client.get(f"/maps/{CORP_SHARED_MAP_ID}/access")
    # App returns 401 NotAuthorizedException for permission errors
    assert response.status_code == 401


# =============================================================================
# SSE Event Tests
# =============================================================================


@pytest.mark.order(70)
async def test_map_updated_event(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify MAP_UPDATED event is published when map is updated."""
    assert test_state.map_id is not None

    # Start SSE collection in background with connection synchronization
    connected = asyncio.Event()
    collect_task = asyncio.create_task(
        collect_sse_events(test_client, test_state.map_id, timeout=1.0, connected_event=connected)
    )
    await asyncio.wait_for(connected.wait(), timeout=1.0)

    # Update the map
    response = await test_client.patch(
        f"/maps/{test_state.map_id}",
        json={"description": "Updated for SSE test"},
    )
    assert response.status_code == 200

    # Collect and verify event
    events = await collect_task
    event = assert_event_published(events, EventType.MAP_UPDATED)
    assert "changes" in event.data


@pytest.mark.order(71)
async def test_access_corporation_granted_event(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify ACCESS_CORPORATION_GRANTED event is published."""
    assert test_state.map_id is not None

    # Start SSE collection in background with connection synchronization
    connected = asyncio.Event()
    collect_task = asyncio.create_task(
        collect_sse_events(test_client, test_state.map_id, timeout=1.0, connected_event=connected)
    )
    await asyncio.wait_for(connected.wait(), timeout=1.0)

    # Add corporation access
    response = await test_client.post(
        f"/maps/{test_state.map_id}/corporations",
        json={"corporation_id": TEST2_CORPORATION_ID, "read_only": True},
    )
    assert response.status_code == 204, f"Failed to add corp access: {response.text}"

    # Collect and verify event
    events = await collect_task
    event = assert_event_published(
        events,
        EventType.ACCESS_CORPORATION_GRANTED,
        corporation_id=TEST2_CORPORATION_ID,
    )
    assert event.data["read_only"] is True


@pytest.mark.order(72)
async def test_access_corporation_revoked_event(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify ACCESS_CORPORATION_REVOKED event is published."""
    assert test_state.map_id is not None

    # Start SSE collection in background with connection synchronization
    connected = asyncio.Event()
    collect_task = asyncio.create_task(
        collect_sse_events(test_client, test_state.map_id, timeout=1.0, connected_event=connected)
    )
    await asyncio.wait_for(connected.wait(), timeout=1.0)

    # Remove corporation access
    response = await test_client.delete(
        f"/maps/{test_state.map_id}/corporations/{TEST2_CORPORATION_ID}",
    )
    assert response.status_code == 204, f"Failed to revoke corp access: {response.text}"

    # Collect and verify event
    events = await collect_task
    assert_event_published(
        events,
        EventType.ACCESS_CORPORATION_REVOKED,
        corporation_id=TEST2_CORPORATION_ID,
    )


@pytest.mark.order(73)
async def test_access_alliance_granted_event(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify ACCESS_ALLIANCE_GRANTED event is published."""
    assert test_state.map_id is not None

    # Start SSE collection in background with connection synchronization
    connected = asyncio.Event()
    collect_task = asyncio.create_task(
        collect_sse_events(test_client, test_state.map_id, timeout=1.0, connected_event=connected)
    )
    await asyncio.wait_for(connected.wait(), timeout=1.0)

    # Add alliance access
    response = await test_client.post(
        f"/maps/{test_state.map_id}/alliances",
        json={"alliance_id": TEST2_ALLIANCE_ID, "read_only": False},
    )
    assert response.status_code == 204, f"Failed to add alliance access: {response.text}"

    # Collect and verify event
    events = await collect_task
    event = assert_event_published(
        events,
        EventType.ACCESS_ALLIANCE_GRANTED,
        alliance_id=TEST2_ALLIANCE_ID,
    )
    assert event.data["read_only"] is False


@pytest.mark.order(74)
async def test_access_alliance_revoked_event(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify ACCESS_ALLIANCE_REVOKED event is published."""
    assert test_state.map_id is not None

    # Start SSE collection in background with connection synchronization
    connected = asyncio.Event()
    collect_task = asyncio.create_task(
        collect_sse_events(test_client, test_state.map_id, timeout=1.0, connected_event=connected)
    )
    await asyncio.wait_for(connected.wait(), timeout=1.0)

    # Remove alliance access
    response = await test_client.delete(
        f"/maps/{test_state.map_id}/alliances/{TEST2_ALLIANCE_ID}",
    )
    assert response.status_code == 204, f"Failed to revoke alliance access: {response.text}"

    # Collect and verify event
    events = await collect_task
    assert_event_published(
        events,
        EventType.ACCESS_ALLIANCE_REVOKED,
        alliance_id=TEST2_ALLIANCE_ID,
    )


@pytest.mark.order(75)
async def test_access_character_granted_event(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify ACCESS_CHARACTER_GRANTED event is published."""
    assert test_state.map_id is not None

    # Start SSE collection in background with connection synchronization
    connected = asyncio.Event()
    collect_task = asyncio.create_task(
        collect_sse_events(test_client, test_state.map_id, timeout=1.0, connected_event=connected)
    )
    await asyncio.wait_for(connected.wait(), timeout=1.0)

    # Add character access
    response = await test_client.post(
        f"/maps/{test_state.map_id}/characters",
        json={"character_id": TEST2_CHARACTER_ID, "read_only": True},
    )
    assert response.status_code == 204, f"Failed to add character access: {response.text}"

    # Collect and verify event
    events = await collect_task
    event = assert_event_published(
        events,
        EventType.ACCESS_CHARACTER_GRANTED,
        character_id=TEST2_CHARACTER_ID,
    )
    assert event.data["read_only"] is True


@pytest.mark.order(76)
async def test_access_character_revoked_event(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify ACCESS_CHARACTER_REVOKED event is published."""
    assert test_state.map_id is not None

    # Start SSE collection in background with connection synchronization
    connected = asyncio.Event()
    collect_task = asyncio.create_task(
        collect_sse_events(test_client, test_state.map_id, timeout=1.0, connected_event=connected)
    )
    await asyncio.wait_for(connected.wait(), timeout=1.0)

    # Remove character access
    response = await test_client.delete(
        f"/maps/{test_state.map_id}/characters/{TEST2_CHARACTER_ID}",
    )
    assert response.status_code == 204, f"Failed to revoke character access: {response.text}"

    # Collect and verify event
    events = await collect_task
    assert_event_published(
        events,
        EventType.ACCESS_CHARACTER_REVOKED,
        character_id=TEST2_CHARACTER_ID,
    )


@pytest.mark.order(80)
async def test_map_deleted_event(
    test_client: AsyncClient,
) -> None:
    """Verify MAP_DELETED event is published when map is deleted.

    This test creates a temporary map and deletes it to avoid
    affecting other tests that depend on test_state.map_id.
    """
    # Create a temporary map for this test
    response = await test_client.post(
        "/maps/",
        json={"name": "Map To Delete For SSE Test"},
    )
    assert response.status_code == 201, f"Failed to create temp map: {response.text}"
    temp_map_id = UUID(response.json()["id"])

    # Start SSE collection in background with connection synchronization
    connected = asyncio.Event()
    collect_task = asyncio.create_task(
        collect_sse_events(test_client, temp_map_id, timeout=1.0, connected_event=connected)
    )
    await asyncio.wait_for(connected.wait(), timeout=1.0)

    # Delete the map
    response = await test_client.delete(f"/maps/{temp_map_id}")
    assert response.status_code == 202, f"Failed to delete map: {response.text}"

    # Collect and verify event
    events = await collect_task
    event = assert_event_published(events, EventType.MAP_DELETED)
    assert "deleted_node_ids" in event.data
    assert "deleted_link_ids" in event.data
