"""Link integration tests.

These tests verify link creation, updating, flipping, and deletion,
as well as the SSE events for each operation.
Tests run in order after node tests (test_02_nodes.py).
"""

from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from routes.maps.events import EventType
from tests.factories.static_data import (
    C140_WORMHOLE_ID,
    J123456_SYSTEM_ID,
    K162_WORMHOLE_ID,
    N944_WORMHOLE_ID,
)
from tests.fixtures.events import collect_sse_events, find_events_of_type
from tests.integration.conftest import IntegrationTestState

# =============================================================================
# Link Creation Tests
# =============================================================================


@pytest.mark.order(200)
async def test_create_link_requires_nodes(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify link creation requires source_node_id and target_node_id."""
    assert test_state.map_id is not None

    # Missing both node IDs
    response = await test_client.post(
        f"/maps/{test_state.map_id}/links",
        json={},
    )
    assert response.status_code == 400

    # Missing target_node_id
    response = await test_client.post(
        f"/maps/{test_state.map_id}/links",
        json={"source_node_id": str(uuid4())},
    )
    assert response.status_code == 400


@pytest.mark.order(201)
async def test_create_link(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Create a link between two nodes.

    First ensures we have two nodes available for linking.
    """
    assert test_state.map_id is not None
    assert len(test_state.node_ids) >= 1, "Need at least one node from previous tests"

    # Create a second node if we don't have one (previous tests may have deleted it)
    if len(test_state.node_ids) < 2:
        response = await test_client.post(
            f"/maps/{test_state.map_id}/nodes",
            json={
                "system_id": J123456_SYSTEM_ID,
                "pos_x": 300.0,
                "pos_y": 400.0,
            },
        )
        assert response.status_code == 201, f"Failed to create second node: {response.text}"
        test_state.node_ids.append(UUID(response.json()["node_id"]))

    source_node_id = test_state.node_ids[0]
    target_node_id = test_state.node_ids[1]

    response = await test_client.post(
        f"/maps/{test_state.map_id}/links",
        json={
            "source_node_id": str(source_node_id),
            "target_node_id": str(target_node_id),
        },
    )
    assert response.status_code == 201, f"Failed to create link: {response.text}"

    data = response.json()
    assert "link_id" in data

    # Store link ID for later tests
    test_state.link_ids.append(UUID(data["link_id"]))


@pytest.mark.order(202)
async def test_create_link_sse_event(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify LINK_CREATED event is published when link is created.

    Creates a temporary link for this test to verify SSE event.
    """
    assert test_state.map_id is not None
    assert len(test_state.node_ids) >= 2

    # Delete existing link first to allow creating a new one between same nodes
    if test_state.link_ids:
        await test_client.delete(
            f"/maps/{test_state.map_id}/links/{test_state.link_ids[0]}",
        )
        test_state.link_ids.clear()

    source_node_id = test_state.node_ids[0]
    target_node_id = test_state.node_ids[1]

    # Start SSE collection in background with connection synchronization
    connected = asyncio.Event()
    collect_task = asyncio.create_task(
        collect_sse_events(test_client, test_state.map_id, timeout=2.0, max_events=50, connected_event=connected)
    )
    await asyncio.wait_for(connected.wait(), timeout=1.0)

    # Create a link
    response = await test_client.post(
        f"/maps/{test_state.map_id}/links",
        json={
            "source_node_id": str(source_node_id),
            "target_node_id": str(target_node_id),
        },
    )
    assert response.status_code == 201, f"Failed to create link: {response.text}"

    link_id = UUID(response.json()["link_id"])
    test_state.link_ids.append(link_id)

    # Collect and verify event
    events = await collect_task
    link_created_events = find_events_of_type(events, EventType.LINK_CREATED)
    matching_events = [e for e in link_created_events if e.data.get("id") == str(link_id)]
    assert len(matching_events) > 0, (
        f"No LINK_CREATED event with id={link_id} found. Got: {[e.data.get('id') for e in link_created_events]}"
    )

    # Verify enriched data is present
    event = matching_events[0]
    assert "source_node_id" in event.data
    assert "target_node_id" in event.data


@pytest.mark.order(203)
async def test_create_link_defaults_to_k162(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify link created without wormhole_id defaults to K162."""
    assert test_state.map_id is not None
    assert len(test_state.link_ids) >= 1

    # Get the map to check link details
    response = await test_client.get(f"/maps/{test_state.map_id}")
    assert response.status_code == 200

    data = response.json()
    links = data.get("links", [])

    # Find our link
    link = next((lnk for lnk in links if lnk["id"] == str(test_state.link_ids[0])), None)
    assert link is not None, "Link not found in map response"

    # Verify it defaults to K162
    assert link["wormhole_code"] == "K162"


@pytest.mark.order(204)
async def test_create_link_with_wormhole_type(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Create a link with a specific wormhole type.

    Creates a third node to make a new link with specific wormhole type.
    """
    assert test_state.map_id is not None

    # Create a third node
    from tests.factories.static_data import J234567_SYSTEM_ID

    response = await test_client.post(
        f"/maps/{test_state.map_id}/nodes",
        json={
            "system_id": J234567_SYSTEM_ID,
            "pos_x": 500.0,
            "pos_y": 500.0,
        },
    )
    assert response.status_code == 201
    third_node_id = UUID(response.json()["node_id"])
    test_state.node_ids.append(third_node_id)

    # Create link with specific wormhole type (N944 - C5 static)
    response = await test_client.post(
        f"/maps/{test_state.map_id}/links",
        json={
            "source_node_id": str(test_state.node_ids[1]),
            "target_node_id": str(third_node_id),
            "wormhole_id": N944_WORMHOLE_ID,
        },
    )
    assert response.status_code == 201, f"Failed to create link: {response.text}"

    link_id = UUID(response.json()["link_id"])
    test_state.link_ids.append(link_id)

    # Verify the wormhole type in map response
    response = await test_client.get(f"/maps/{test_state.map_id}")
    assert response.status_code == 200

    links = response.json().get("links", [])
    link = next((lnk for lnk in links if lnk["id"] == str(link_id)), None)
    assert link is not None
    assert link["wormhole_code"] == "N944"


# =============================================================================
# Link Update Tests
# =============================================================================


@pytest.mark.order(210)
async def test_update_link_wormhole_type(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Update a link's wormhole type."""
    assert test_state.map_id is not None
    assert len(test_state.link_ids) >= 1

    link_id = test_state.link_ids[0]

    # Update to C140 (lowsec static)
    response = await test_client.patch(
        f"/maps/{test_state.map_id}/links/{link_id}",
        json={"wormhole_id": C140_WORMHOLE_ID},
    )
    assert response.status_code == 200, f"Failed to update link: {response.text}"

    data = response.json()
    assert data["link_id"] == str(link_id)

    # Verify in map response
    response = await test_client.get(f"/maps/{test_state.map_id}")
    links = response.json().get("links", [])
    link = next((lnk for lnk in links if lnk["id"] == str(link_id)), None)
    assert link is not None
    assert link["wormhole_code"] == "C140"


@pytest.mark.order(211)
async def test_update_link_lifetime_status(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Update a link's lifetime status."""
    assert test_state.map_id is not None
    assert len(test_state.link_ids) >= 1

    link_id = test_state.link_ids[0]

    # Update to EOL status
    response = await test_client.patch(
        f"/maps/{test_state.map_id}/links/{link_id}",
        json={"lifetime_status": "eol"},
    )
    assert response.status_code == 200, f"Failed to update link: {response.text}"

    # Verify in map response
    response = await test_client.get(f"/maps/{test_state.map_id}")
    links = response.json().get("links", [])
    link = next((lnk for lnk in links if lnk["id"] == str(link_id)), None)
    assert link is not None
    assert link["lifetime_status"] == "eol"


@pytest.mark.order(212)
async def test_update_link_mass_usage(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Update a link's mass usage."""
    assert test_state.map_id is not None
    assert len(test_state.link_ids) >= 1

    link_id = test_state.link_ids[0]

    # Update mass usage
    response = await test_client.patch(
        f"/maps/{test_state.map_id}/links/{link_id}",
        json={"mass_usage": 500000000},  # 500M kg
    )
    assert response.status_code == 200, f"Failed to update link: {response.text}"

    # Verify in map response
    response = await test_client.get(f"/maps/{test_state.map_id}")
    links = response.json().get("links", [])
    link = next((lnk for lnk in links if lnk["id"] == str(link_id)), None)
    assert link is not None
    assert link["mass_usage"] == 500000000


@pytest.mark.order(213)
async def test_update_link_sse_event(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify LINK_UPDATED event is published when link is updated."""
    assert test_state.map_id is not None
    assert len(test_state.link_ids) >= 1

    link_id = test_state.link_ids[0]

    # Start SSE collection
    connected = asyncio.Event()
    collect_task = asyncio.create_task(
        collect_sse_events(test_client, test_state.map_id, timeout=2.0, max_events=50, connected_event=connected)
    )
    await asyncio.wait_for(connected.wait(), timeout=1.0)

    # Update the link
    response = await test_client.patch(
        f"/maps/{test_state.map_id}/links/{link_id}",
        json={"lifetime_status": "stable"},
    )
    assert response.status_code == 200

    # Collect and verify event
    events = await collect_task
    link_updated_events = find_events_of_type(events, EventType.LINK_UPDATED)
    matching_events = [
        e for e in link_updated_events if e.data.get("id") == str(link_id) and e.data.get("lifetime_status") == "stable"
    ]
    assert len(matching_events) > 0, (
        f"No LINK_UPDATED event with id={link_id} and lifetime_status=stable found. "
        f"Got: {[e.data for e in link_updated_events]}"
    )


@pytest.mark.order(214)
async def test_update_nonexistent_link_returns_404(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify 404 is returned for nonexistent link."""
    assert test_state.map_id is not None

    fake_link_id = uuid4()

    response = await test_client.patch(
        f"/maps/{test_state.map_id}/links/{fake_link_id}",
        json={"wormhole_id": K162_WORMHOLE_ID},
    )
    assert response.status_code == 404


# =============================================================================
# Link Flip/Reverse Tests
# =============================================================================


@pytest.mark.order(220)
async def test_flip_link_direction(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Flip a link's direction using reverse=true."""
    assert test_state.map_id is not None
    assert len(test_state.link_ids) >= 1

    link_id = test_state.link_ids[0]

    # Get current direction
    response = await test_client.get(f"/maps/{test_state.map_id}")
    links = response.json().get("links", [])
    link = next((lnk for lnk in links if lnk["id"] == str(link_id)), None)
    assert link is not None

    original_source = link["source_node_id"]
    original_target = link["target_node_id"]

    # Flip the link
    response = await test_client.patch(
        f"/maps/{test_state.map_id}/links/{link_id}",
        json={"reverse": True},
    )
    assert response.status_code == 200, f"Failed to flip link: {response.text}"

    # Verify direction is flipped
    response = await test_client.get(f"/maps/{test_state.map_id}")
    links = response.json().get("links", [])
    link = next((lnk for lnk in links if lnk["id"] == str(link_id)), None)
    assert link is not None
    assert link["source_node_id"] == original_target
    assert link["target_node_id"] == original_source


@pytest.mark.order(221)
async def test_set_link_type_from_source(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Set link type from the source node (no flip)."""
    assert test_state.map_id is not None
    assert len(test_state.link_ids) >= 1

    link_id = test_state.link_ids[0]

    # Get current source node
    response = await test_client.get(f"/maps/{test_state.map_id}")
    links = response.json().get("links", [])
    link = next((lnk for lnk in links if lnk["id"] == str(link_id)), None)
    assert link is not None

    source_node_id = link["source_node_id"]
    target_node_id = link["target_node_id"]

    # Set type from source - should not flip
    response = await test_client.patch(
        f"/maps/{test_state.map_id}/links/{link_id}/set-type",
        json={
            "wormhole_id": N944_WORMHOLE_ID,
            "from_node_id": source_node_id,
        },
    )
    assert response.status_code == 200, f"Failed to set link type: {response.text}"

    # Verify direction is unchanged
    response = await test_client.get(f"/maps/{test_state.map_id}")
    links = response.json().get("links", [])
    link = next((lnk for lnk in links if lnk["id"] == str(link_id)), None)
    assert link is not None
    assert link["source_node_id"] == source_node_id
    assert link["target_node_id"] == target_node_id
    assert link["wormhole_code"] == "N944"


@pytest.mark.order(222)
async def test_set_link_type_from_target(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Set link type from the target node (auto-flips)."""
    assert test_state.map_id is not None
    assert len(test_state.link_ids) >= 1

    link_id = test_state.link_ids[0]

    # Get current direction
    response = await test_client.get(f"/maps/{test_state.map_id}")
    links = response.json().get("links", [])
    link = next((lnk for lnk in links if lnk["id"] == str(link_id)), None)
    assert link is not None

    original_source = link["source_node_id"]
    original_target = link["target_node_id"]

    # Set type from target - should auto-flip
    response = await test_client.patch(
        f"/maps/{test_state.map_id}/links/{link_id}/set-type",
        json={
            "wormhole_id": C140_WORMHOLE_ID,
            "from_node_id": original_target,  # This is currently the target
        },
    )
    assert response.status_code == 200, f"Failed to set link type: {response.text}"

    # Verify direction is flipped
    response = await test_client.get(f"/maps/{test_state.map_id}")
    links = response.json().get("links", [])
    link = next((lnk for lnk in links if lnk["id"] == str(link_id)), None)
    assert link is not None
    assert link["source_node_id"] == original_target
    assert link["target_node_id"] == original_source
    assert link["wormhole_code"] == "C140"


@pytest.mark.order(223)
async def test_flip_link_sse_event(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify LINK_UPDATED event is published when link is flipped."""
    assert test_state.map_id is not None
    assert len(test_state.link_ids) >= 1

    link_id = test_state.link_ids[0]

    # Start SSE collection
    connected = asyncio.Event()
    collect_task = asyncio.create_task(
        collect_sse_events(test_client, test_state.map_id, timeout=2.0, max_events=50, connected_event=connected)
    )
    await asyncio.wait_for(connected.wait(), timeout=1.0)

    # Flip the link
    response = await test_client.patch(
        f"/maps/{test_state.map_id}/links/{link_id}",
        json={"reverse": True},
    )
    assert response.status_code == 200

    # Collect and verify event
    events = await collect_task
    link_updated_events = find_events_of_type(events, EventType.LINK_UPDATED)
    matching_events = [e for e in link_updated_events if e.data.get("id") == str(link_id)]
    assert len(matching_events) > 0, (
        f"No LINK_UPDATED event with id={link_id} found after flip. "
        f"Got: {[e.data.get('id') for e in link_updated_events]}"
    )


# =============================================================================
# Link Deletion Tests
# =============================================================================


@pytest.mark.order(230)
async def test_delete_link(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Delete a link and verify response."""
    assert test_state.map_id is not None
    assert len(test_state.link_ids) >= 2

    # Delete the second link (N944 one created in test_create_link_with_wormhole_type)
    link_id = test_state.link_ids[1]

    response = await test_client.delete(
        f"/maps/{test_state.map_id}/links/{link_id}",
    )
    assert response.status_code == 202, f"Failed to delete link: {response.text}"

    data = response.json()
    assert data["link_id"] == str(link_id)

    # Remove from test_state
    test_state.link_ids.remove(link_id)


@pytest.mark.order(231)
async def test_delete_link_sse_event(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify LINK_DELETED event is published when link is deleted.

    Creates a temporary link for this test.
    """
    assert test_state.map_id is not None
    assert len(test_state.node_ids) >= 2

    # Delete any existing link between these nodes first to ensure clean state
    if test_state.link_ids:
        await test_client.delete(
            f"/maps/{test_state.map_id}/links/{test_state.link_ids[0]}",
        )
        test_state.link_ids.clear()

    # Create a fresh temporary link
    response = await test_client.post(
        f"/maps/{test_state.map_id}/links",
        json={
            "source_node_id": str(test_state.node_ids[0]),
            "target_node_id": str(test_state.node_ids[1]),
            "wormhole_id": K162_WORMHOLE_ID,
        },
    )
    assert response.status_code == 201, f"Failed to create temp link: {response.text}"
    temp_link_id = UUID(response.json()["link_id"])

    # Start SSE collection
    connected = asyncio.Event()
    collect_task = asyncio.create_task(
        collect_sse_events(test_client, test_state.map_id, timeout=2.0, max_events=50, connected_event=connected)
    )
    await asyncio.wait_for(connected.wait(), timeout=1.0)

    # Delete the link
    response = await test_client.delete(
        f"/maps/{test_state.map_id}/links/{temp_link_id}",
    )
    assert response.status_code == 202

    # Collect and verify event
    events = await collect_task
    link_deleted_events = find_events_of_type(events, EventType.LINK_DELETED)
    matching_events = [e for e in link_deleted_events if e.data.get("link_id") == str(temp_link_id)]
    assert len(matching_events) > 0, (
        f"No LINK_DELETED event with link_id={temp_link_id} found. Got: {[e.data for e in link_deleted_events]}"
    )


@pytest.mark.order(232)
async def test_delete_nonexistent_link_returns_404(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify 404 is returned for nonexistent or already-deleted link."""
    assert test_state.map_id is not None

    fake_link_id = uuid4()

    response = await test_client.delete(
        f"/maps/{test_state.map_id}/links/{fake_link_id}",
    )
    assert response.status_code == 404


@pytest.mark.order(233)
async def test_deleted_link_not_in_map_response(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify deleted links are not returned in map detail response."""
    assert test_state.map_id is not None

    # Get map detail
    response = await test_client.get(f"/maps/{test_state.map_id}")
    assert response.status_code == 200

    data = response.json()
    links = data.get("links", [])

    # Get all remaining link IDs from test_state
    remaining_link_ids = {str(lid) for lid in test_state.link_ids}

    # Get all link IDs from the response
    response_link_ids = {lnk["id"] for lnk in links}

    # All links in response should match our remaining set exactly
    assert response_link_ids == remaining_link_ids, (
        f"Response links don't match expected. Expected: {remaining_link_ids}, Got: {response_link_ids}"
    )
