"""Route calculation integration tests.

These tests verify route calculation through the wormhole chain,
including on-chain routes and routes to off-chain k-space destinations.
Tests use a pre-seeded map with a small wormhole chain:
  Jita <-> J123456 <-> J345678 <-> HED-GP

Note: test_state fixture is required as a dependency to ensure authentication
runs first (via pytest-order), even though it's not directly used in these tests.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.factories.static_data import (
    AMARR_SYSTEM_ID,
    HED_GP_SYSTEM_ID,
    J123456_SYSTEM_ID,
    J345678_SYSTEM_ID,
    JITA_SYSTEM_ID,
    ROUTE_NODE_HED_GP_ID,
    ROUTE_NODE_J123456_ID,
    ROUTE_NODE_JITA_ID,
    ROUTE_TEST_MAP_ID,
)
from tests.integration.conftest import IntegrationTestState

# =============================================================================
# Route Calculation Tests - On-Chain Routes
# =============================================================================


@pytest.mark.order(500)
async def test_route_on_chain_adjacent_nodes(
    test_client: AsyncClient,
    test_state: IntegrationTestState,  # noqa: ARG001
) -> None:
    """Test route between adjacent nodes on the chain."""
    response = await test_client.get(
        f"/routes/{ROUTE_TEST_MAP_ID}",
        params={
            "origin": ROUTE_NODE_JITA_ID,
            "destination": J123456_SYSTEM_ID,
            "route_type": "shortest",
        },
    )
    assert response.status_code == 200, f"Route calculation failed: {response.text}"

    data = response.json()
    assert data["destination_on_chain"] is True
    assert data["total_jumps"] == 1
    assert data["wormhole_jumps"] == 1
    assert data["kspace_jumps"] == 0
    assert len(data["waypoints"]) == 2

    # Verify waypoint system IDs
    assert data["waypoints"][0]["system_id"] == JITA_SYSTEM_ID
    assert data["waypoints"][1]["system_id"] == J123456_SYSTEM_ID


@pytest.mark.order(501)
async def test_route_on_chain_multiple_hops(
    test_client: AsyncClient,
    test_state: IntegrationTestState,  # noqa: ARG001
) -> None:
    """Test route across multiple wormhole jumps on the chain."""
    response = await test_client.get(
        f"/routes/{ROUTE_TEST_MAP_ID}",
        params={
            "origin": ROUTE_NODE_JITA_ID,
            "destination": HED_GP_SYSTEM_ID,
            "route_type": "shortest",
        },
    )
    assert response.status_code == 200, f"Route calculation failed: {response.text}"

    data = response.json()
    assert data["destination_on_chain"] is True
    assert data["total_jumps"] == 3
    assert data["wormhole_jumps"] == 3
    assert data["kspace_jumps"] == 0
    assert len(data["waypoints"]) == 4

    # Verify the route goes through all systems in order
    system_ids = [wp["system_id"] for wp in data["waypoints"]]
    assert system_ids == [JITA_SYSTEM_ID, J123456_SYSTEM_ID, J345678_SYSTEM_ID, HED_GP_SYSTEM_ID]


@pytest.mark.order(502)
async def test_route_on_chain_from_middle(
    test_client: AsyncClient,
    test_state: IntegrationTestState,  # noqa: ARG001
) -> None:
    """Test route starting from a middle node on the chain."""
    response = await test_client.get(
        f"/routes/{ROUTE_TEST_MAP_ID}",
        params={
            "origin": ROUTE_NODE_J123456_ID,
            "destination": HED_GP_SYSTEM_ID,
            "route_type": "shortest",
        },
    )
    assert response.status_code == 200, f"Route calculation failed: {response.text}"

    data = response.json()
    assert data["destination_on_chain"] is True
    assert data["total_jumps"] == 2
    assert data["wormhole_jumps"] == 2

    system_ids = [wp["system_id"] for wp in data["waypoints"]]
    assert system_ids == [J123456_SYSTEM_ID, J345678_SYSTEM_ID, HED_GP_SYSTEM_ID]


@pytest.mark.order(503)
async def test_route_on_chain_reverse_direction(
    test_client: AsyncClient,
    test_state: IntegrationTestState,  # noqa: ARG001
) -> None:
    """Test route in reverse direction (links are bidirectional)."""
    response = await test_client.get(
        f"/routes/{ROUTE_TEST_MAP_ID}",
        params={
            "origin": ROUTE_NODE_HED_GP_ID,
            "destination": JITA_SYSTEM_ID,
            "route_type": "shortest",
        },
    )
    assert response.status_code == 200, f"Route calculation failed: {response.text}"

    data = response.json()
    assert data["destination_on_chain"] is True
    assert data["total_jumps"] == 3

    # Verify reverse route
    system_ids = [wp["system_id"] for wp in data["waypoints"]]
    assert system_ids == [HED_GP_SYSTEM_ID, J345678_SYSTEM_ID, J123456_SYSTEM_ID, JITA_SYSTEM_ID]


# =============================================================================
# Route Calculation Tests - Off-Chain Destinations
# =============================================================================


@pytest.mark.order(510)
async def test_route_off_chain_from_kspace_exit(
    test_client: AsyncClient,
    test_state: IntegrationTestState,  # noqa: ARG001
) -> None:
    """Test route to off-chain destination via nearest k-space exit (Jita -> Amarr)."""
    response = await test_client.get(
        f"/routes/{ROUTE_TEST_MAP_ID}",
        params={
            "origin": ROUTE_NODE_JITA_ID,
            "destination": AMARR_SYSTEM_ID,
            "route_type": "shortest",
        },
    )
    assert response.status_code == 200, f"Route calculation failed: {response.text}"

    data = response.json()
    assert data["destination_on_chain"] is False
    # Route should be: Jita (on chain) -> ... -> Amarr (off chain via ESI)
    # The wormhole jumps should be 0 since Jita is already k-space
    assert data["wormhole_jumps"] == 0
    assert data["kspace_jumps"] > 0

    # First waypoint should be Jita, last should be Amarr
    assert data["waypoints"][0]["system_id"] == JITA_SYSTEM_ID
    assert data["waypoints"][-1]["system_id"] == AMARR_SYSTEM_ID
    assert data["waypoints"][-1]["node_id"] is None  # Off-chain


@pytest.mark.order(511)
async def test_route_off_chain_from_wspace(
    test_client: AsyncClient,
    test_state: IntegrationTestState,  # noqa: ARG001
) -> None:
    """Test route from w-space to off-chain destination (finds best exit)."""
    response = await test_client.get(
        f"/routes/{ROUTE_TEST_MAP_ID}",
        params={
            "origin": ROUTE_NODE_J123456_ID,
            "destination": AMARR_SYSTEM_ID,
            "route_type": "shortest",
        },
    )
    assert response.status_code == 200, f"Route calculation failed: {response.text}"

    data = response.json()
    assert data["destination_on_chain"] is False
    # Route must go through wormholes to exit to k-space
    assert data["wormhole_jumps"] >= 1
    assert data["kspace_jumps"] > 0

    # First waypoint is origin
    assert data["waypoints"][0]["system_id"] == J123456_SYSTEM_ID
    # Last waypoint is destination (off-chain)
    assert data["waypoints"][-1]["system_id"] == AMARR_SYSTEM_ID


# =============================================================================
# Route Calculation Tests - Route Types
# =============================================================================


@pytest.mark.order(520)
async def test_route_secure_type(
    test_client: AsyncClient,
    test_state: IntegrationTestState,  # noqa: ARG001
) -> None:
    """Test secure route type."""
    response = await test_client.get(
        f"/routes/{ROUTE_TEST_MAP_ID}",
        params={
            "origin": ROUTE_NODE_JITA_ID,
            "destination": J123456_SYSTEM_ID,
            "route_type": "secure",
        },
    )
    assert response.status_code == 200, f"Route calculation failed: {response.text}"

    data = response.json()
    assert data["route_type"] == "secure"


@pytest.mark.order(521)
async def test_route_invalid_type_rejected(
    test_client: AsyncClient,
    test_state: IntegrationTestState,  # noqa: ARG001
) -> None:
    """Test that invalid route type is rejected."""
    response = await test_client.get(
        f"/routes/{ROUTE_TEST_MAP_ID}",
        params={
            "origin": ROUTE_NODE_JITA_ID,
            "destination": J123456_SYSTEM_ID,
            "route_type": "invalid",
        },
    )
    assert response.status_code == 400


# =============================================================================
# Route Calculation Tests - Error Cases
# =============================================================================


@pytest.mark.order(530)
async def test_route_invalid_origin_node(
    test_client: AsyncClient,
    test_state: IntegrationTestState,  # noqa: ARG001
) -> None:
    """Test that invalid origin node returns 404."""
    fake_node_id = "00000000-0000-0000-0000-000000009999"
    response = await test_client.get(
        f"/routes/{ROUTE_TEST_MAP_ID}",
        params={
            "origin": fake_node_id,
            "destination": J123456_SYSTEM_ID,
            "route_type": "shortest",
        },
    )
    assert response.status_code == 404


@pytest.mark.order(531)
async def test_route_no_access_to_map(
    test_client: AsyncClient,
    test_state: IntegrationTestState,  # noqa: ARG001
) -> None:
    """Test that route calculation requires map access."""
    # Use a non-existent map ID
    fake_map_id = "00000000-0000-0000-0000-000000009999"
    response = await test_client.get(
        f"/routes/{fake_map_id}",
        params={
            "origin": ROUTE_NODE_JITA_ID,
            "destination": J123456_SYSTEM_ID,
            "route_type": "shortest",
        },
    )
    # Should be 401 (no access) or 404 (not found)
    assert response.status_code in [401, 404]


@pytest.mark.order(532)
async def test_route_same_origin_destination(
    test_client: AsyncClient,
    test_state: IntegrationTestState,  # noqa: ARG001
) -> None:
    """Test route when origin and destination are the same system."""
    response = await test_client.get(
        f"/routes/{ROUTE_TEST_MAP_ID}",
        params={
            "origin": ROUTE_NODE_JITA_ID,
            "destination": JITA_SYSTEM_ID,
            "route_type": "shortest",
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert data["total_jumps"] == 0
    assert len(data["waypoints"]) == 1
    assert data["waypoints"][0]["system_id"] == JITA_SYSTEM_ID


# =============================================================================
# Route Calculation Tests - K-Space Bridge Routing
# =============================================================================


@pytest.mark.order(540)
async def test_route_kspace_bridge_on_chain_destination(
    test_client: AsyncClient,
    test_state: IntegrationTestState,  # noqa: ARG001
) -> None:
    """Test that k-space bridges are considered for on-chain destinations.

    The test map has: Jita <-> J123456 <-> J345678 <-> HED-GP
    This is 3 wormhole jumps from Jita to HED-GP.

    If the k-space route between Jita and HED-GP (both on chain) is shorter
    than 3 jumps, the algorithm should prefer the k-space bridge.
    If it's longer, it should prefer the wormhole route.

    Either way, the route should be valid and reach the destination.
    """
    response = await test_client.get(
        f"/routes/{ROUTE_TEST_MAP_ID}",
        params={
            "origin": ROUTE_NODE_JITA_ID,
            "destination": HED_GP_SYSTEM_ID,
            "route_type": "shortest",
        },
    )
    assert response.status_code == 200, f"Route calculation failed: {response.text}"

    data = response.json()
    assert data["destination_on_chain"] is True

    # Verify route starts at Jita and ends at HED-GP
    assert data["waypoints"][0]["system_id"] == JITA_SYSTEM_ID
    assert data["waypoints"][-1]["system_id"] == HED_GP_SYSTEM_ID

    # The route should have found either:
    # 1. Pure wormhole route (3 WH jumps, 0 k-space)
    # 2. K-space bridge (0 WH jumps, N k-space jumps)
    # The algorithm picks whichever is shorter
    assert data["total_jumps"] > 0

    # Verify consistency: total = wormhole + kspace
    assert data["total_jumps"] == data["wormhole_jumps"] + data["kspace_jumps"]


@pytest.mark.order(541)
async def test_route_kspace_bridge_from_wspace_origin(
    test_client: AsyncClient,
    test_state: IntegrationTestState,  # noqa: ARG001
) -> None:
    """Test k-space bridge routing when starting from w-space.

    Starting from J123456 (w-space), going to HED-GP (on chain).
    Pure wormhole route: J123456 -> J345678 -> HED-GP (2 WH jumps)
    Bridge option: J123456 -> Jita (1 WH) -> k-space -> HED-GP

    The algorithm should compare both options and choose the shortest.
    """
    response = await test_client.get(
        f"/routes/{ROUTE_TEST_MAP_ID}",
        params={
            "origin": ROUTE_NODE_J123456_ID,
            "destination": HED_GP_SYSTEM_ID,
            "route_type": "shortest",
        },
    )
    assert response.status_code == 200, f"Route calculation failed: {response.text}"

    data = response.json()
    assert data["destination_on_chain"] is True

    # Verify route endpoints
    assert data["waypoints"][0]["system_id"] == J123456_SYSTEM_ID
    assert data["waypoints"][-1]["system_id"] == HED_GP_SYSTEM_ID

    # Must have at least 1 wormhole jump (can't leave w-space without one)
    assert data["wormhole_jumps"] >= 1
    assert data["total_jumps"] == data["wormhole_jumps"] + data["kspace_jumps"]


@pytest.mark.order(542)
async def test_route_kspace_bridge_secure_mode(
    test_client: AsyncClient,
    test_state: IntegrationTestState,  # noqa: ARG001
) -> None:
    """Test k-space bridge routing with secure route type.

    In secure mode, wormhole jumps are weighted more heavily (5x).
    This should make k-space bridges more attractive when available.
    """
    response = await test_client.get(
        f"/routes/{ROUTE_TEST_MAP_ID}",
        params={
            "origin": ROUTE_NODE_JITA_ID,
            "destination": HED_GP_SYSTEM_ID,
            "route_type": "secure",
        },
    )
    assert response.status_code == 200, f"Route calculation failed: {response.text}"

    data = response.json()
    assert data["route_type"] == "secure"
    assert data["destination_on_chain"] is True

    # Route should be valid
    assert data["waypoints"][0]["system_id"] == JITA_SYSTEM_ID
    assert data["waypoints"][-1]["system_id"] == HED_GP_SYSTEM_ID
    assert data["total_jumps"] == data["wormhole_jumps"] + data["kspace_jumps"]


@pytest.mark.order(543)
async def test_route_kspace_bridge_off_chain_destination(
    test_client: AsyncClient,
    test_state: IntegrationTestState,  # noqa: ARG001
) -> None:
    """Test k-space bridge for off-chain destination.

    Starting from HED-GP (null-sec on chain), going to Amarr (off-chain).
    The algorithm should consider:
    1. Direct: HED-GP -> ESI route to Amarr
    2. Bridge: HED-GP -> WH -> J345678 -> WH -> J123456 -> WH -> Jita -> ESI to Amarr

    It should pick whichever total route is shorter.
    """
    response = await test_client.get(
        f"/routes/{ROUTE_TEST_MAP_ID}",
        params={
            "origin": ROUTE_NODE_HED_GP_ID,
            "destination": AMARR_SYSTEM_ID,
            "route_type": "shortest",
        },
    )
    assert response.status_code == 200, f"Route calculation failed: {response.text}"

    data = response.json()
    assert data["destination_on_chain"] is False

    # Verify route endpoints
    assert data["waypoints"][0]["system_id"] == HED_GP_SYSTEM_ID
    assert data["waypoints"][-1]["system_id"] == AMARR_SYSTEM_ID
    assert data["waypoints"][-1]["node_id"] is None  # Off-chain

    # Must have k-space jumps to reach off-chain destination
    assert data["kspace_jumps"] > 0
    assert data["total_jumps"] == data["wormhole_jumps"] + data["kspace_jumps"]


@pytest.mark.order(544)
async def test_route_kspace_bridge_waypoints_include_intermediate_systems(
    test_client: AsyncClient,
    test_state: IntegrationTestState,  # noqa: ARG001
) -> None:
    """Test that k-space bridge routes include intermediate waypoints.

    When a k-space bridge is used, the response should include all
    intermediate k-space systems in the waypoints list, not just endpoints.
    """
    response = await test_client.get(
        f"/routes/{ROUTE_TEST_MAP_ID}",
        params={
            "origin": ROUTE_NODE_JITA_ID,
            "destination": AMARR_SYSTEM_ID,
            "route_type": "shortest",
        },
    )
    assert response.status_code == 200, f"Route calculation failed: {response.text}"

    data = response.json()

    # This route goes from Jita (on-chain) to Amarr (off-chain)
    # It should have intermediate k-space waypoints
    if data["kspace_jumps"] > 1:
        # Find waypoints that are k-space (node_id is None or is_wormhole_jump is False)
        kspace_waypoints = [
            wp
            for wp in data["waypoints"][1:]  # Skip origin
            if not wp["is_wormhole_jump"]
        ]
        # Should have multiple k-space waypoints if kspace_jumps > 1
        assert len(kspace_waypoints) >= 1
