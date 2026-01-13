"""Signature integration tests.

These tests verify signature creation, updating, bulk operations, and deletion,
as well as the SSE events for each operation.
Tests run in order after link tests (test_03_links.py).
"""

from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from routes.maps.events import EventType
from tests.factories.static_data import (
    C140_WORMHOLE_ID,
    K162_WORMHOLE_ID,
)
from tests.fixtures.events import collect_sse_events, find_events_of_type
from tests.integration.conftest import IntegrationTestState

# =============================================================================
# Signature Creation Tests
# =============================================================================


@pytest.mark.order(300)
async def test_create_signature_requires_node(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify signature creation requires node_id."""
    assert test_state.map_id is not None

    # Missing node_id
    response = await test_client.post(
        f"/maps/{test_state.map_id}/signatures",
        json={
            "code": "ABC-123",
            "group_type": "signature",
        },
    )
    assert response.status_code == 400


@pytest.mark.order(301)
async def test_create_signature(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Create a signature with code and group_type."""
    assert test_state.map_id is not None
    assert len(test_state.node_ids) >= 1

    node_id = test_state.node_ids[0]

    response = await test_client.post(
        f"/maps/{test_state.map_id}/signatures",
        json={
            "node_id": str(node_id),
            "code": "abc-123",  # Should be auto-uppercased
            "group_type": "signature",
            "subgroup": "data",
        },
    )
    assert response.status_code == 201, f"Failed to create signature: {response.text}"

    data = response.json()
    assert "signature_id" in data

    # Store signature ID for later tests
    test_state.signature_ids.append(UUID(data["signature_id"]))


@pytest.mark.order(302)
async def test_create_signature_sse_event(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify SIGNATURE_CREATED event is published when signature is created."""
    assert test_state.map_id is not None
    assert len(test_state.node_ids) >= 1

    node_id = test_state.node_ids[0]

    # Start SSE collection
    connected = asyncio.Event()
    collect_task = asyncio.create_task(
        collect_sse_events(test_client, test_state.map_id, timeout=2.0, max_events=50, connected_event=connected)
    )
    await asyncio.wait_for(connected.wait(), timeout=1.0)

    # Create a signature
    response = await test_client.post(
        f"/maps/{test_state.map_id}/signatures",
        json={
            "node_id": str(node_id),
            "code": "DEF-456",
            "group_type": "signature",
            "subgroup": "relic",
        },
    )
    assert response.status_code == 201, f"Failed to create signature: {response.text}"

    sig_id = UUID(response.json()["signature_id"])
    test_state.signature_ids.append(sig_id)

    # Collect and verify event
    events = await collect_task
    sig_created_events = find_events_of_type(events, EventType.SIGNATURE_CREATED)
    matching_events = [e for e in sig_created_events if e.data.get("id") == str(sig_id)]
    assert len(matching_events) > 0, (
        f"No SIGNATURE_CREATED event with id={sig_id} found. Got: {[e.data.get('id') for e in sig_created_events]}"
    )

    # Verify enriched data
    event = matching_events[0]
    assert event.data["code"] == "DEF-456"
    assert event.data["subgroup"] == "relic"


@pytest.mark.order(303)
async def test_create_signature_with_wormhole_type(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Create a wormhole signature with wormhole_id."""
    assert test_state.map_id is not None
    assert len(test_state.node_ids) >= 1

    node_id = test_state.node_ids[0]

    response = await test_client.post(
        f"/maps/{test_state.map_id}/signatures",
        json={
            "node_id": str(node_id),
            "code": "GHI-789",
            "group_type": "signature",
            "subgroup": "wormhole",
            "wormhole_id": K162_WORMHOLE_ID,
        },
    )
    assert response.status_code == 201, f"Failed to create signature: {response.text}"

    sig_id = UUID(response.json()["signature_id"])
    test_state.signature_ids.append(sig_id)

    # Verify wormhole code in node signatures
    response = await test_client.get(f"/maps/{test_state.map_id}/nodes/{node_id}/signatures")
    assert response.status_code == 200

    sigs = response.json().get("signatures", [])
    sig = next((s for s in sigs if s["id"] == str(sig_id)), None)
    assert sig is not None
    assert sig["wormhole_code"] == "K162"


# =============================================================================
# Signature Update Tests
# =============================================================================


@pytest.mark.order(310)
async def test_update_signature_code(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Update a signature's code (should be auto-uppercased)."""
    assert test_state.map_id is not None
    assert len(test_state.signature_ids) >= 1

    sig_id = test_state.signature_ids[0]

    response = await test_client.patch(
        f"/maps/{test_state.map_id}/signatures/{sig_id}",
        json={"code": "xyz-999"},  # Should be uppercased
    )
    assert response.status_code == 200, f"Failed to update signature: {response.text}"

    # Verify in node signatures
    node_id = test_state.node_ids[0]
    response = await test_client.get(f"/maps/{test_state.map_id}/nodes/{node_id}/signatures")
    assert response.status_code == 200

    sigs = response.json().get("signatures", [])
    sig = next((s for s in sigs if s["id"] == str(sig_id)), None)
    assert sig is not None
    assert sig["code"] == "XYZ-999"  # Uppercased


@pytest.mark.order(311)
async def test_update_signature_subgroup(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Update a signature's subgroup."""
    assert test_state.map_id is not None
    assert len(test_state.signature_ids) >= 1

    sig_id = test_state.signature_ids[0]

    response = await test_client.patch(
        f"/maps/{test_state.map_id}/signatures/{sig_id}",
        json={"subgroup": "gas"},
    )
    assert response.status_code == 200, f"Failed to update signature: {response.text}"

    # Verify in node signatures
    node_id = test_state.node_ids[0]
    response = await test_client.get(f"/maps/{test_state.map_id}/nodes/{node_id}/signatures")
    sigs = response.json().get("signatures", [])
    sig = next((s for s in sigs if s["id"] == str(sig_id)), None)
    assert sig is not None
    assert sig["subgroup"] == "gas"


@pytest.mark.order(312)
async def test_update_signature_wormhole_type(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Update a signature's wormhole_id."""
    assert test_state.map_id is not None
    assert len(test_state.signature_ids) >= 3  # We need the wormhole signature

    # Use the wormhole signature (GHI-789)
    sig_id = test_state.signature_ids[2]

    response = await test_client.patch(
        f"/maps/{test_state.map_id}/signatures/{sig_id}",
        json={"wormhole_id": C140_WORMHOLE_ID},
    )
    assert response.status_code == 200, f"Failed to update signature: {response.text}"

    # Verify in node signatures
    node_id = test_state.node_ids[0]
    response = await test_client.get(f"/maps/{test_state.map_id}/nodes/{node_id}/signatures")
    sigs = response.json().get("signatures", [])
    sig = next((s for s in sigs if s["id"] == str(sig_id)), None)
    assert sig is not None
    assert sig["wormhole_code"] == "C140"


@pytest.mark.order(313)
async def test_update_signature_sse_event(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify SIGNATURE_UPDATED event is published when signature is updated."""
    assert test_state.map_id is not None
    assert len(test_state.signature_ids) >= 1

    sig_id = test_state.signature_ids[0]

    # Start SSE collection
    connected = asyncio.Event()
    collect_task = asyncio.create_task(
        collect_sse_events(test_client, test_state.map_id, timeout=2.0, max_events=50, connected_event=connected)
    )
    await asyncio.wait_for(connected.wait(), timeout=1.0)

    # Update the signature
    response = await test_client.patch(
        f"/maps/{test_state.map_id}/signatures/{sig_id}",
        json={"subgroup": "combat"},
    )
    assert response.status_code == 200

    # Collect and verify event
    events = await collect_task
    sig_updated_events = find_events_of_type(events, EventType.SIGNATURE_UPDATED)
    matching_events = [
        e for e in sig_updated_events if e.data.get("id") == str(sig_id) and e.data.get("subgroup") == "combat"
    ]
    assert len(matching_events) > 0, (
        f"No SIGNATURE_UPDATED event with id={sig_id} and subgroup=combat found. "
        f"Got: {[e.data for e in sig_updated_events]}"
    )


@pytest.mark.order(314)
async def test_update_nonexistent_signature_returns_404(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify 404 is returned for nonexistent signature."""
    assert test_state.map_id is not None

    fake_sig_id = uuid4()

    response = await test_client.patch(
        f"/maps/{test_state.map_id}/signatures/{fake_sig_id}",
        json={"code": "ZZZ-000"},
    )
    assert response.status_code == 404


# =============================================================================
# Signature Bulk Operations Tests
# =============================================================================


@pytest.mark.order(320)
async def test_bulk_create_signatures(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Bulk create multiple signatures."""
    assert test_state.map_id is not None
    assert len(test_state.node_ids) >= 1

    node_id = test_state.node_ids[0]

    response = await test_client.post(
        f"/maps/{test_state.map_id}/nodes/{node_id}/signatures/bulk",
        json={
            "signatures": [
                {"code": "BLK-001", "group_type": "signature", "subgroup": "data"},
                {"code": "BLK-002", "group_type": "signature", "subgroup": "relic"},
                {"code": "BLK-003", "group_type": "anomaly", "subgroup": "combat"},
            ]
        },
    )
    assert response.status_code == 201, f"Failed to bulk create: {response.text}"

    data = response.json()
    assert "created" in data
    assert "updated" in data
    assert "deleted" in data

    # Should have created 3 new signatures
    assert len(data["created"]) == 3
    assert len(data["updated"]) == 0
    assert len(data["deleted"]) == 0

    # Store IDs for later
    for sig_id in data["created"]:
        test_state.signature_ids.append(UUID(sig_id))


@pytest.mark.order(321)
async def test_bulk_update_signatures(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Bulk update existing signatures."""
    assert test_state.map_id is not None
    assert len(test_state.node_ids) >= 1

    node_id = test_state.node_ids[0]

    # Update existing signatures by code
    response = await test_client.post(
        f"/maps/{test_state.map_id}/nodes/{node_id}/signatures/bulk",
        json={
            "signatures": [
                {"code": "BLK-001", "group_type": "signature", "subgroup": "gas"},  # Changed
                {"code": "BLK-002", "group_type": "signature", "subgroup": "ore"},  # Changed
            ]
        },
    )
    assert response.status_code == 201, f"Failed to bulk update: {response.text}"

    data = response.json()
    assert len(data["created"]) == 0  # No new
    assert len(data["updated"]) == 2  # Two updated

    # Verify changes in node signatures
    response = await test_client.get(f"/maps/{test_state.map_id}/nodes/{node_id}/signatures")
    sigs = response.json().get("signatures", [])

    blk001 = next((s for s in sigs if s["code"] == "BLK-001"), None)
    assert blk001 is not None
    assert blk001["subgroup"] == "gas"

    blk002 = next((s for s in sigs if s["code"] == "BLK-002"), None)
    assert blk002 is not None
    assert blk002["subgroup"] == "ore"


@pytest.mark.order(322)
async def test_bulk_delete_missing_signatures(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Bulk with delete_missing=true deletes signatures not in request."""
    assert test_state.map_id is not None
    assert len(test_state.node_ids) >= 1

    node_id = test_state.node_ids[0]

    # Get current signature count
    response = await test_client.get(f"/maps/{test_state.map_id}/nodes/{node_id}/signatures")
    initial_sigs = response.json().get("signatures", [])
    initial_count = len(initial_sigs)
    assert initial_count >= 3, f"Expected at least 3 signatures, got {initial_count}"

    # Bulk upsert with only 2 signatures and delete_missing=true
    response = await test_client.post(
        f"/maps/{test_state.map_id}/nodes/{node_id}/signatures/bulk",
        params={"delete_missing": "true"},
        json={
            "signatures": [
                {"code": "KEEP-001", "group_type": "signature", "subgroup": "data"},
                {"code": "KEEP-002", "group_type": "signature", "subgroup": "relic"},
            ]
        },
    )
    assert response.status_code == 201, f"Failed to bulk with delete: {response.text}"

    data = response.json()
    # Should have created 2 and deleted others
    assert len(data["created"]) == 2
    assert len(data["deleted"]) >= 1  # At least some deleted

    # Verify only KEEP signatures remain
    response = await test_client.get(f"/maps/{test_state.map_id}/nodes/{node_id}/signatures")
    sigs = response.json().get("signatures", [])
    codes = {s["code"] for s in sigs}
    assert "KEEP-001" in codes
    assert "KEEP-002" in codes

    # Clear and update our tracking
    test_state.signature_ids.clear()
    for sig in sigs:
        test_state.signature_ids.append(UUID(sig["id"]))


@pytest.mark.order(323)
async def test_bulk_signatures_sse_event(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify SIGNATURES_BULK_UPDATED event is published."""
    assert test_state.map_id is not None
    assert len(test_state.node_ids) >= 1

    node_id = test_state.node_ids[0]

    # Start SSE collection
    connected = asyncio.Event()
    collect_task = asyncio.create_task(
        collect_sse_events(test_client, test_state.map_id, timeout=2.0, max_events=50, connected_event=connected)
    )
    await asyncio.wait_for(connected.wait(), timeout=1.0)

    # Bulk create a new signature
    response = await test_client.post(
        f"/maps/{test_state.map_id}/nodes/{node_id}/signatures/bulk",
        json={
            "signatures": [
                {"code": "SSE-001", "group_type": "signature", "subgroup": "wormhole"},
            ]
        },
    )
    assert response.status_code == 201

    # Collect and verify event
    events = await collect_task
    bulk_events = find_events_of_type(events, EventType.SIGNATURES_BULK_UPDATED)
    matching_events = [e for e in bulk_events if e.data.get("node_id") == str(node_id)]
    assert len(matching_events) > 0, (
        f"No SIGNATURES_BULK_UPDATED event with node_id={node_id} found. Got: {[e.data for e in bulk_events]}"
    )

    # Verify structure
    event = matching_events[0]
    assert "created_ids" in event.data
    assert "updated_ids" in event.data
    assert "deleted_ids" in event.data


@pytest.mark.order(324)
async def test_bulk_empty_request(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Empty signature list is handled gracefully."""
    assert test_state.map_id is not None
    assert len(test_state.node_ids) >= 1

    node_id = test_state.node_ids[0]

    response = await test_client.post(
        f"/maps/{test_state.map_id}/nodes/{node_id}/signatures/bulk",
        json={"signatures": []},
    )
    assert response.status_code == 201, f"Failed with empty list: {response.text}"

    data = response.json()
    assert data["created"] == []
    assert data["updated"] == []
    assert data["deleted"] == []


# =============================================================================
# Signature Deletion Tests
# =============================================================================


@pytest.mark.order(330)
async def test_delete_signature(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Delete a signature and verify response."""
    assert test_state.map_id is not None
    assert len(test_state.signature_ids) >= 1

    sig_id = test_state.signature_ids[0]

    response = await test_client.delete(
        f"/maps/{test_state.map_id}/signatures/{sig_id}",
    )
    assert response.status_code == 202, f"Failed to delete signature: {response.text}"

    data = response.json()
    assert data["signature_id"] == str(sig_id)

    # Track as deleted and remove from active list
    test_state.deleted_signature_ids.append(sig_id)
    test_state.signature_ids.remove(sig_id)


@pytest.mark.order(331)
async def test_delete_signature_sse_event(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify SIGNATURE_DELETED event is published when signature is deleted."""
    assert test_state.map_id is not None
    assert len(test_state.node_ids) >= 1

    node_id = test_state.node_ids[0]

    # Get the current last event_id to filter out history when we connect to SSE
    drain_events = await collect_sse_events(test_client, test_state.map_id, timeout=0.5, max_events=100)
    last_event_id = drain_events[-1].event_id if drain_events else "0"

    # Create a temporary signature for deletion
    response = await test_client.post(
        f"/maps/{test_state.map_id}/signatures",
        json={
            "node_id": str(node_id),
            "code": "DEL-SSE",
            "group_type": "signature",
        },
    )
    assert response.status_code == 201
    temp_sig_id = UUID(response.json()["signature_id"])

    # Start SSE collection, filtering out events up to and including last_event_id
    connected = asyncio.Event()
    collect_task = asyncio.create_task(
        collect_sse_events(
            test_client,
            test_state.map_id,
            timeout=2.0,
            max_events=10,
            connected_event=connected,
            last_event_id=last_event_id,
        )
    )
    await asyncio.wait_for(connected.wait(), timeout=1.0)

    # Delete the signature
    response = await test_client.delete(
        f"/maps/{test_state.map_id}/signatures/{temp_sig_id}",
    )
    assert response.status_code == 202

    # Collect events
    events = await collect_task

    # Find the delete event for our signature
    sig_deleted_events = find_events_of_type(events, EventType.SIGNATURE_DELETED)
    matching_events = [e for e in sig_deleted_events if e.data.get("signature_id") == str(temp_sig_id)]
    assert len(matching_events) > 0, (
        f"No SIGNATURE_DELETED event with signature_id={temp_sig_id} found. "
        f"All events: {[(e.event_id, e.event_type.value) for e in events]}. "
        f"Delete events: {[(e.event_id, e.data) for e in sig_deleted_events]}"
    )


@pytest.mark.order(332)
async def test_delete_nonexistent_signature_returns_404(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify 404 is returned for nonexistent or already-deleted signature."""
    assert test_state.map_id is not None

    fake_sig_id = uuid4()

    response = await test_client.delete(
        f"/maps/{test_state.map_id}/signatures/{fake_sig_id}",
    )
    assert response.status_code == 404


@pytest.mark.order(333)
async def test_get_node_signatures_excludes_deleted(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify deleted signatures are not returned in node signatures response."""
    assert test_state.map_id is not None
    assert len(test_state.node_ids) >= 1
    assert len(test_state.deleted_signature_ids) >= 1, "Need at least one deleted signature to verify exclusion"

    node_id = test_state.node_ids[0]

    # Get current signatures
    response = await test_client.get(f"/maps/{test_state.map_id}/nodes/{node_id}/signatures")
    assert response.status_code == 200

    sigs = response.json().get("signatures", [])
    returned_sig_ids = {sig["id"] for sig in sigs}

    # Verify deleted signatures are NOT in the response
    for deleted_id in test_state.deleted_signature_ids:
        assert str(deleted_id) not in returned_sig_ids, f"Deleted signature {deleted_id} should not be in response"

    # Verify all returned signatures have valid structure
    for sig in sigs:
        assert "id" in sig
        assert "code" in sig
        assert "group_type" in sig
