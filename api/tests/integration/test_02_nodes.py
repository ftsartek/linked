"""Node integration tests.

These tests verify node creation, updating, locking, and deletion,
as well as the SSE events for each operation.
Tests run in order after map tests (test_01_maps.py).
"""

from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from routes.maps.events import EventType
from tests.factories.static_data import (
    ALLIANCE_MAP_NODE_ID,
    ALLIANCE_SHARED_MAP_ID,
    CORP_MAP_NODE_ID,
    CORP_SHARED_MAP_ID,
    J123456_SYSTEM_ID,
    JITA_SYSTEM_ID,
    PERIMETER_SYSTEM_ID,
)
from tests.fixtures.events import assert_event_published, collect_sse_events
from tests.integration.conftest import IntegrationTestState

# =============================================================================
# Node Creation Tests
# =============================================================================


@pytest.mark.order(100)
async def test_create_node_requires_system_id(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify node creation requires system_id field."""
    assert test_state.map_id is not None

    response = await test_client.post(
        f"/maps/{test_state.map_id}/nodes",
        json={"pos_x": 0.0, "pos_y": 0.0},  # Missing system_id
    )
    assert response.status_code == 400


@pytest.mark.order(101)
async def test_create_node_requires_position(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify node creation requires pos_x and pos_y fields."""
    assert test_state.map_id is not None

    response = await test_client.post(
        f"/maps/{test_state.map_id}/nodes",
        json={"system_id": JITA_SYSTEM_ID},  # Missing position
    )
    assert response.status_code == 400


@pytest.mark.order(102)
async def test_create_node(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Create a node with Jita system."""
    assert test_state.map_id is not None

    response = await test_client.post(
        f"/maps/{test_state.map_id}/nodes",
        json={
            "system_id": JITA_SYSTEM_ID,
            "pos_x": 100.0,
            "pos_y": 200.0,
        },
    )
    assert response.status_code == 201, f"Failed to create node: {response.text}"

    data = response.json()
    assert "node_id" in data

    # Store node ID for later tests
    test_state.node_ids.append(UUID(data["node_id"]))


@pytest.mark.order(103)
async def test_create_node_sse_event(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify NODE_CREATED event is published when node is created."""
    assert test_state.map_id is not None

    # Start SSE collection in background with connection synchronization
    # Use higher max_events to account for event history
    connected = asyncio.Event()
    collect_task = asyncio.create_task(
        collect_sse_events(test_client, test_state.map_id, timeout=2.0, max_events=50, connected_event=connected)
    )
    await asyncio.wait_for(connected.wait(), timeout=1.0)

    # Create a second node
    response = await test_client.post(
        f"/maps/{test_state.map_id}/nodes",
        json={
            "system_id": J123456_SYSTEM_ID,
            "pos_x": 300.0,
            "pos_y": 400.0,
        },
    )
    assert response.status_code == 201, f"Failed to create node: {response.text}"

    data = response.json()
    node_id = UUID(data["node_id"])
    test_state.node_ids.append(node_id)

    # Collect and verify event - filter by system_id to find the right event
    events = await collect_task
    event = assert_event_published(events, EventType.NODE_CREATED, system_id=J123456_SYSTEM_ID)
    assert event.data["id"] == str(node_id)


@pytest.mark.order(104)
async def test_create_duplicate_node_fails(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify creating a node for the same system fails."""
    assert test_state.map_id is not None

    # Try to create another node for Jita (already created in test_create_node)
    response = await test_client.post(
        f"/maps/{test_state.map_id}/nodes",
        json={
            "system_id": JITA_SYSTEM_ID,
            "pos_x": 500.0,
            "pos_y": 600.0,
        },
    )
    # Should fail - duplicate system on same map (conflict)
    assert response.status_code == 409, f"Expected 409 conflict for duplicate: {response.text}"


# =============================================================================
# Node Position Update Tests
# =============================================================================


@pytest.mark.order(110)
async def test_update_node_position(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Update a node's position."""
    assert test_state.map_id is not None
    assert len(test_state.node_ids) > 0

    node_id = test_state.node_ids[0]

    response = await test_client.patch(
        f"/maps/{test_state.map_id}/nodes/{node_id}/position",
        json={"pos_x": 150.0, "pos_y": 250.0},
    )
    assert response.status_code == 200, f"Failed to update node position: {response.text}"

    data = response.json()
    assert data["node_id"] == str(node_id)


@pytest.mark.order(111)
async def test_update_node_position_sse_event(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify NODE_UPDATED event is published when node position is updated."""
    assert test_state.map_id is not None
    assert len(test_state.node_ids) > 0

    node_id = test_state.node_ids[0]

    # Start SSE collection in background with connection synchronization
    # Use higher max_events to account for event history
    connected = asyncio.Event()
    collect_task = asyncio.create_task(
        collect_sse_events(test_client, test_state.map_id, timeout=2.0, max_events=50, connected_event=connected)
    )
    await asyncio.wait_for(connected.wait(), timeout=1.0)

    # Update node position
    response = await test_client.patch(
        f"/maps/{test_state.map_id}/nodes/{node_id}/position",
        json={"pos_x": 175.0, "pos_y": 275.0},
    )
    assert response.status_code == 200

    # Collect and verify event - filter by exact position to find the new event
    events = await collect_task
    from tests.fixtures.events import find_events_of_type

    node_updated_events = find_events_of_type(events, EventType.NODE_UPDATED)
    matching_events = [
        e for e in node_updated_events if e.data.get("id") == str(node_id) and e.data.get("pos_x") == 175.0
    ]
    assert len(matching_events) > 0, (
        f"No NODE_UPDATED event with pos_x=175.0 found. Got: {[e.data for e in node_updated_events]}"
    )


@pytest.mark.order(112)
async def test_cannot_update_node_on_readonly_map(
    test_client: AsyncClient,
    test_state: IntegrationTestState,  # noqa: ARG001
) -> None:
    """Verify position update is blocked on read-only shared map."""
    # Use the preseeded node on the alliance shared map (read-only access)
    response = await test_client.patch(
        f"/maps/{ALLIANCE_SHARED_MAP_ID}/nodes/{ALLIANCE_MAP_NODE_ID}/position",
        json={"pos_x": 200.0, "pos_y": 200.0},
    )
    # Should fail due to read-only access (401 for permission error)
    assert response.status_code == 401


@pytest.mark.order(113)
async def test_update_nonexistent_node_returns_404(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify 404 is returned for nonexistent node."""
    assert test_state.map_id is not None

    fake_node_id = uuid4()

    response = await test_client.patch(
        f"/maps/{test_state.map_id}/nodes/{fake_node_id}/position",
        json={"pos_x": 100.0, "pos_y": 100.0},
    )
    assert response.status_code == 404


# =============================================================================
# Node System Update Tests
# =============================================================================


@pytest.mark.order(120)
async def test_update_node_system(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Update a node's system."""
    assert test_state.map_id is not None
    assert len(test_state.node_ids) > 0

    node_id = test_state.node_ids[0]

    # Change from Jita to Perimeter
    response = await test_client.patch(
        f"/maps/{test_state.map_id}/nodes/{node_id}/system",
        json={"system_id": PERIMETER_SYSTEM_ID},
    )
    assert response.status_code == 200, f"Failed to update node system: {response.text}"

    data = response.json()
    assert data["node_id"] == str(node_id)


@pytest.mark.order(121)
async def test_update_node_system_sse_event(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify NODE_UPDATED event is published when node system is updated."""
    assert test_state.map_id is not None
    assert len(test_state.node_ids) > 0

    node_id = test_state.node_ids[0]

    # Start SSE collection in background with connection synchronization
    # Use higher max_events to account for event history
    connected = asyncio.Event()
    collect_task = asyncio.create_task(
        collect_sse_events(test_client, test_state.map_id, timeout=2.0, max_events=50, connected_event=connected)
    )
    await asyncio.wait_for(connected.wait(), timeout=1.0)

    # Change back to Jita
    response = await test_client.patch(
        f"/maps/{test_state.map_id}/nodes/{node_id}/system",
        json={"system_id": JITA_SYSTEM_ID},
    )
    assert response.status_code == 200

    # Collect and verify event - filter by exact system_id to find the new event
    events = await collect_task
    from tests.fixtures.events import find_events_of_type

    node_updated_events = find_events_of_type(events, EventType.NODE_UPDATED)
    matching_events = [
        e for e in node_updated_events if e.data.get("id") == str(node_id) and e.data.get("system_id") == JITA_SYSTEM_ID
    ]
    assert len(matching_events) > 0, (
        f"No NODE_UPDATED event with system_id={JITA_SYSTEM_ID} found. Got: {[e.data for e in node_updated_events]}"
    )


@pytest.mark.order(122)
async def test_update_node_invalid_system_fails(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify updating to invalid system_id fails."""
    assert test_state.map_id is not None
    assert len(test_state.node_ids) > 0

    node_id = test_state.node_ids[0]

    response = await test_client.patch(
        f"/maps/{test_state.map_id}/nodes/{node_id}/system",
        json={"system_id": 999999999},  # Invalid system ID
    )
    # Should fail - invalid system (bad request)
    assert response.status_code == 400


# =============================================================================
# Node Lock Tests
# =============================================================================


@pytest.mark.order(130)
async def test_lock_node_owner_only(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Owner can lock a node."""
    assert test_state.map_id is not None
    assert len(test_state.node_ids) > 0

    node_id = test_state.node_ids[0]

    response = await test_client.patch(
        f"/maps/{test_state.map_id}/nodes/{node_id}/locked",
        json={"locked": True},
    )
    assert response.status_code == 200, f"Failed to lock node: {response.text}"

    data = response.json()
    assert data["node_id"] == str(node_id)


@pytest.mark.order(131)
async def test_lock_node_sse_event(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify NODE_UPDATED event is published when node is locked."""
    assert test_state.map_id is not None
    assert len(test_state.node_ids) > 1

    # Use second node for this test
    node_id = test_state.node_ids[1]

    # Start SSE collection in background with connection synchronization
    # Use higher max_events to account for event history
    connected = asyncio.Event()
    collect_task = asyncio.create_task(
        collect_sse_events(test_client, test_state.map_id, timeout=2.0, max_events=50, connected_event=connected)
    )
    await asyncio.wait_for(connected.wait(), timeout=1.0)

    # Lock the node
    response = await test_client.patch(
        f"/maps/{test_state.map_id}/nodes/{node_id}/locked",
        json={"locked": True},
    )
    assert response.status_code == 200

    # Collect and verify event - filter by node id to find the right event
    events = await collect_task
    event = assert_event_published(events, EventType.NODE_UPDATED, id=str(node_id))
    assert event.data["locked"] is True


@pytest.mark.order(132)
async def test_cannot_move_locked_node(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify position update on locked node returns 409 CONFLICT."""
    assert test_state.map_id is not None
    assert len(test_state.node_ids) > 0

    node_id = test_state.node_ids[0]  # This node was locked in test_lock_node_owner_only

    response = await test_client.patch(
        f"/maps/{test_state.map_id}/nodes/{node_id}/position",
        json={"pos_x": 999.0, "pos_y": 999.0},
    )
    assert response.status_code == 409, f"Expected 409 for locked node: {response.text}"


@pytest.mark.order(133)
async def test_cannot_change_locked_node_system(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify system update on locked node returns 409 CONFLICT."""
    assert test_state.map_id is not None
    assert len(test_state.node_ids) > 0

    node_id = test_state.node_ids[0]  # This node was locked in test_lock_node_owner_only

    response = await test_client.patch(
        f"/maps/{test_state.map_id}/nodes/{node_id}/system",
        json={"system_id": PERIMETER_SYSTEM_ID},
    )
    assert response.status_code == 409, f"Expected 409 for locked node: {response.text}"


@pytest.mark.order(134)
async def test_unlock_node(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Owner can unlock a node."""
    assert test_state.map_id is not None
    assert len(test_state.node_ids) > 0

    node_id = test_state.node_ids[0]

    response = await test_client.patch(
        f"/maps/{test_state.map_id}/nodes/{node_id}/locked",
        json={"locked": False},
    )
    assert response.status_code == 200, f"Failed to unlock node: {response.text}"

    data = response.json()
    assert data["node_id"] == str(node_id)


@pytest.mark.order(135)
async def test_can_move_unlocked_node(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify position update succeeds after unlock."""
    assert test_state.map_id is not None
    assert len(test_state.node_ids) > 0

    node_id = test_state.node_ids[0]

    response = await test_client.patch(
        f"/maps/{test_state.map_id}/nodes/{node_id}/position",
        json={"pos_x": 200.0, "pos_y": 300.0},
    )
    assert response.status_code == 200, f"Failed to move unlocked node: {response.text}"


@pytest.mark.order(136)
async def test_non_owner_cannot_lock_node(
    test_client: AsyncClient,
) -> None:
    """Verify non-owner with edit access cannot lock/unlock nodes.

    Uses the corp shared map where test user has write access but is not owner.
    """
    # Corp shared map has read_only=false, so we have edit access but not ownership
    # Use the preseeded node on the corp shared map
    response = await test_client.patch(
        f"/maps/{CORP_SHARED_MAP_ID}/nodes/{CORP_MAP_NODE_ID}/locked",
        json={"locked": True},
    )
    # Should fail with 401 (owner only operation)
    assert response.status_code == 401


# =============================================================================
# Node Deletion Tests
# =============================================================================


@pytest.mark.order(140)
async def test_delete_node(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Delete a node and verify cascade info returned."""
    assert test_state.map_id is not None
    assert len(test_state.node_ids) > 1

    # Delete the second node (J123456)
    node_id = test_state.node_ids[1]

    response = await test_client.delete(
        f"/maps/{test_state.map_id}/nodes/{node_id}",
    )
    assert response.status_code == 202, f"Failed to delete node: {response.text}"

    data = response.json()
    assert data["node_id"] == str(node_id)
    assert "deleted_link_ids" in data
    assert "deleted_signature_ids" in data

    # Remove from test_state since it's deleted
    test_state.node_ids.remove(node_id)


@pytest.mark.order(141)
async def test_delete_node_sse_event(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify NODE_DELETED event is published when node is deleted.

    Creates a temporary node for this test to avoid affecting other tests.
    """
    assert test_state.map_id is not None

    # Create a temporary node for deletion
    from tests.factories.static_data import J345678_SYSTEM_ID

    response = await test_client.post(
        f"/maps/{test_state.map_id}/nodes",
        json={
            "system_id": J345678_SYSTEM_ID,
            "pos_x": 500.0,
            "pos_y": 500.0,
        },
    )
    assert response.status_code == 201
    temp_node_id = UUID(response.json()["node_id"])

    # Start SSE collection in background with connection synchronization
    # Use higher max_events to account for event history
    connected = asyncio.Event()
    collect_task = asyncio.create_task(
        collect_sse_events(test_client, test_state.map_id, timeout=2.0, max_events=50, connected_event=connected)
    )
    await asyncio.wait_for(connected.wait(), timeout=1.0)

    # Delete the node
    response = await test_client.delete(
        f"/maps/{test_state.map_id}/nodes/{temp_node_id}",
    )
    assert response.status_code == 202

    # Collect and verify event - filter by node_id to find the right event
    events = await collect_task
    assert_event_published(events, EventType.NODE_DELETED, node_id=str(temp_node_id))


@pytest.mark.order(142)
async def test_delete_nonexistent_node_returns_404(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify 404 is returned for nonexistent or already-deleted node."""
    assert test_state.map_id is not None

    fake_node_id = uuid4()

    response = await test_client.delete(
        f"/maps/{test_state.map_id}/nodes/{fake_node_id}",
    )
    assert response.status_code == 404


@pytest.mark.order(143)
async def test_deleted_node_not_in_map_response(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify deleted nodes are not returned in map detail response."""
    assert test_state.map_id is not None

    # Get map detail
    response = await test_client.get(f"/maps/{test_state.map_id}")
    assert response.status_code == 200

    data = response.json()
    nodes = data.get("nodes", [])

    # The second node (J123456) was deleted in test_delete_node
    # The temp node (J345678) was deleted in test_delete_node_sse_event
    # Only the first node (Jita) should remain
    assert len(nodes) == 1
    assert nodes[0]["system_name"] == "Jita"
