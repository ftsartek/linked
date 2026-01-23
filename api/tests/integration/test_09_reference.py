"""Reference endpoint integration tests.

These tests verify the public reference data endpoints which provide
wormhole type information without requiring authentication.

Note: test_state fixture is required as a dependency to ensure authentication
runs first (via pytest-order), even though it's not directly used in these tests.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.factories.static_data import (
    J123456_SYSTEM_ID,
    J234567_SYSTEM_ID,
    J345678_SYSTEM_ID,
    K162_WORMHOLE_ID,
    N944_WORMHOLE_ID,
)
from tests.integration.conftest import IntegrationTestState

# =============================================================================
# List Wormholes Tests
# =============================================================================


@pytest.mark.order(700)
async def test_list_wormholes(
    test_client: AsyncClient,
    test_state: IntegrationTestState,  # noqa: ARG001
) -> None:
    """Test listing all wormhole types returns expected structure."""
    response = await test_client.get("/reference/wormholes")
    assert response.status_code == 200, f"Failed to list wormholes: {response.text}"

    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 4  # At least K162, C140, N944, H296 from preseed

    # Verify structure of items
    for item in data:
        assert "id" in item
        assert "code" in item
        assert "target_class" in item
        assert "sources" in item
        # Verify types
        assert isinstance(item["id"], int)
        assert isinstance(item["code"], str)
        assert item["target_class"] is None or isinstance(item["target_class"], int)
        assert item["sources"] is None or isinstance(item["sources"], list)


@pytest.mark.order(701)
async def test_list_wormholes_contains_known_types(
    test_client: AsyncClient,
    test_state: IntegrationTestState,  # noqa: ARG001
) -> None:
    """Test that known wormhole types from preseed are present."""
    response = await test_client.get("/reference/wormholes")
    assert response.status_code == 200

    data = response.json()
    codes = {item["code"] for item in data}

    # Verify all preseeded wormhole types are present
    assert "K162" in codes
    assert "C140" in codes
    assert "N944" in codes
    assert "H296" in codes


@pytest.mark.order(702)
async def test_list_wormholes_unauthenticated(
    unauthenticated_client: AsyncClient,
) -> None:
    """Test that listing wormholes works without authentication."""
    response = await unauthenticated_client.get("/reference/wormholes")
    assert response.status_code == 200, f"Public endpoint should not require auth: {response.text}"

    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 4


# =============================================================================
# Get Wormhole Detail Tests
# =============================================================================


@pytest.mark.order(710)
async def test_get_wormhole_detail_k162(
    test_client: AsyncClient,
    test_state: IntegrationTestState,  # noqa: ARG001
) -> None:
    """Test getting K162 wormhole details."""
    response = await test_client.get(f"/reference/wormholes/{K162_WORMHOLE_ID}")
    assert response.status_code == 200, f"Failed to get wormhole details: {response.text}"

    data = response.json()

    # Verify required fields
    assert data["id"] == K162_WORMHOLE_ID
    assert data["code"] == "K162"
    assert "target_class" in data
    assert "target_name" in data
    assert "sources" in data
    assert "source_names" in data
    assert "lifetime" in data
    assert "mass_total" in data
    assert "mass_jump_max" in data
    assert "mass_regen" in data

    # K162 has 24hr lifetime
    assert data["lifetime"] == 24.0

    # Verify types
    assert isinstance(data["target_name"], str)
    assert isinstance(data["source_names"], list)


@pytest.mark.order(711)
async def test_get_wormhole_detail_with_target_class(
    test_client: AsyncClient,
    test_state: IntegrationTestState,  # noqa: ARG001
) -> None:
    """Test getting wormhole details with target class mapping."""
    # N944 has target_class=5 (C5)
    response = await test_client.get(f"/reference/wormholes/{N944_WORMHOLE_ID}")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == N944_WORMHOLE_ID
    assert data["code"] == "N944"
    assert data["target_class"] == 5
    assert data["target_name"] == "C5"


@pytest.mark.order(712)
async def test_get_wormhole_detail_unauthenticated(
    unauthenticated_client: AsyncClient,
) -> None:
    """Test that getting wormhole details works without authentication."""
    response = await unauthenticated_client.get(f"/reference/wormholes/{K162_WORMHOLE_ID}")
    assert response.status_code == 200, f"Public endpoint should not require auth: {response.text}"

    data = response.json()
    assert data["code"] == "K162"


@pytest.mark.order(713)
async def test_get_wormhole_not_found(
    test_client: AsyncClient,
    test_state: IntegrationTestState,  # noqa: ARG001
) -> None:
    """Test that non-existent wormhole ID returns 404."""
    non_existent_id = 99999
    response = await test_client.get(f"/reference/wormholes/{non_existent_id}")
    assert response.status_code == 404


@pytest.mark.order(714)
async def test_get_wormhole_invalid_id(
    test_client: AsyncClient,
    test_state: IntegrationTestState,  # noqa: ARG001
) -> None:
    """Test that invalid wormhole ID format returns 404.

    Note: Litestar's path parameter validation returns 404 for type mismatches,
    treating them as "path not found" rather than "bad request".
    """
    response = await test_client.get("/reference/wormholes/not-a-number")
    assert response.status_code == 404


# =============================================================================
# List Wormhole Systems Tests
# =============================================================================


def _flatten_systems(data: dict) -> list[dict]:
    """Extract all systems from the grouped response structure."""
    systems = []
    for region in data.get("regions", []):
        for constellation in region.get("constellations", []):
            for system in constellation.get("systems", []):
                # Add region/constellation info to system for easier testing
                systems.append(
                    {
                        **system,
                        "region_id": region["id"],
                        "region_name": region["name"],
                        "constellation_id": constellation["id"],
                        "constellation_name": constellation["name"],
                    }
                )
    return systems


@pytest.mark.order(720)
async def test_list_wormhole_systems(
    test_client: AsyncClient,
    test_state: IntegrationTestState,  # noqa: ARG001
) -> None:
    """Test listing all wormhole systems returns expected grouped structure."""
    response = await test_client.get("/reference/systems")
    assert response.status_code == 200, f"Failed to list wormhole systems: {response.text}"

    data = response.json()
    assert isinstance(data, dict)
    assert "regions" in data
    assert "total_systems" in data
    assert isinstance(data["regions"], list)
    assert data["total_systems"] >= 3  # At least J123456, J234567, J345678 from preseed

    # Verify region structure
    for region in data["regions"]:
        assert "id" in region
        assert "name" in region
        assert "constellations" in region
        assert isinstance(region["id"], int)
        assert isinstance(region["name"], str)
        assert isinstance(region["constellations"], list)

        # Verify constellation structure
        for constellation in region["constellations"]:
            assert "id" in constellation
            assert "name" in constellation
            assert "systems" in constellation
            assert isinstance(constellation["id"], int)
            assert isinstance(constellation["name"], str)
            assert isinstance(constellation["systems"], list)

            # Verify system structure
            for system in constellation["systems"]:
                assert "id" in system
                assert "name" in system
                assert "system_class" in system
                assert "class_name" in system
                assert "effect_id" in system
                assert "effect_name" in system
                assert "shattered" in system
                assert "statics" in system
                # Verify types
                assert isinstance(system["id"], int)
                assert isinstance(system["name"], str)
                assert isinstance(system["system_class"], int)
                assert isinstance(system["class_name"], str)
                assert isinstance(system["shattered"], bool)
                assert isinstance(system["statics"], list)


@pytest.mark.order(721)
async def test_list_wormhole_systems_contains_known_systems(
    test_client: AsyncClient,
    test_state: IntegrationTestState,  # noqa: ARG001
) -> None:
    """Test that known wormhole systems from preseed are present."""
    response = await test_client.get("/reference/systems")
    assert response.status_code == 200

    data = response.json()
    systems = _flatten_systems(data)
    system_ids = {s["id"] for s in systems}

    # Verify all preseeded wormhole systems are present
    assert J123456_SYSTEM_ID in system_ids
    assert J234567_SYSTEM_ID in system_ids
    assert J345678_SYSTEM_ID in system_ids


@pytest.mark.order(722)
async def test_list_wormhole_systems_with_statics(
    test_client: AsyncClient,
    test_state: IntegrationTestState,  # noqa: ARG001
) -> None:
    """Test that systems include their static wormhole connections."""
    response = await test_client.get("/reference/systems")
    assert response.status_code == 200

    data = response.json()
    systems = _flatten_systems(data)

    # Find J123456 (C3 with C140 static)
    j123456 = next((s for s in systems if s["id"] == J123456_SYSTEM_ID), None)
    assert j123456 is not None
    assert len(j123456["statics"]) >= 1
    c140_static = next((s for s in j123456["statics"] if s["code"] == "C140"), None)
    assert c140_static is not None
    # Verify target_class and target_name are present
    assert "target_class" in c140_static
    assert "target_name" in c140_static

    # Find J234567 (C5 with N944 static -> C5)
    j234567 = next((s for s in systems if s["id"] == J234567_SYSTEM_ID), None)
    assert j234567 is not None
    assert len(j234567["statics"]) >= 1
    n944_static = next((s for s in j234567["statics"] if s["code"] == "N944"), None)
    assert n944_static is not None
    assert n944_static["target_class"] == 5  # C5
    assert n944_static["target_name"] == "C5"


@pytest.mark.order(723)
async def test_list_wormhole_systems_with_effects(
    test_client: AsyncClient,
    test_state: IntegrationTestState,  # noqa: ARG001
) -> None:
    """Test that systems include their wormhole effects."""
    response = await test_client.get("/reference/systems")
    assert response.status_code == 200

    data = response.json()
    systems = _flatten_systems(data)

    # Find J123456 (C3 with Black Hole effect)
    j123456 = next((s for s in systems if s["id"] == J123456_SYSTEM_ID), None)
    assert j123456 is not None
    assert j123456["effect_id"] == 1
    assert j123456["effect_name"] == "Black Hole"

    # Find J234567 (C5 with Magnetar effect)
    j234567 = next((s for s in systems if s["id"] == J234567_SYSTEM_ID), None)
    assert j234567 is not None
    assert j234567["effect_id"] == 2
    assert j234567["effect_name"] == "Magnetar"

    # Find J345678 (C3 without effect)
    j345678 = next((s for s in systems if s["id"] == J345678_SYSTEM_ID), None)
    assert j345678 is not None
    assert j345678["effect_id"] is None
    assert j345678["effect_name"] is None


@pytest.mark.order(724)
async def test_list_wormhole_systems_unauthenticated(
    unauthenticated_client: AsyncClient,
) -> None:
    """Test that listing wormhole systems works without authentication."""
    response = await unauthenticated_client.get("/reference/systems")
    assert response.status_code == 200, f"Public endpoint should not require auth: {response.text}"

    data = response.json()
    assert isinstance(data, dict)
    assert "regions" in data
    assert "total_systems" in data
    assert data["total_systems"] >= 3


@pytest.mark.order(725)
async def test_list_wormhole_systems_grouping(
    test_client: AsyncClient,
    test_state: IntegrationTestState,  # noqa: ARG001
) -> None:
    """Test that systems are correctly grouped by region and constellation."""
    response = await test_client.get("/reference/systems")
    assert response.status_code == 200

    data = response.json()

    # Verify regions are sorted by name
    region_names = [r["name"] for r in data["regions"]]
    assert region_names == sorted(region_names)

    # Verify constellations are sorted by name within each region
    for region in data["regions"]:
        constellation_names = [c["name"] for c in region["constellations"]]
        assert constellation_names == sorted(constellation_names)

        # Verify systems are sorted by name within each constellation
        for constellation in region["constellations"]:
            system_names = [s["name"] for s in constellation["systems"]]
            assert system_names == sorted(system_names)


# =============================================================================
# Filter Wormhole Systems Tests
# =============================================================================


@pytest.mark.order(730)
async def test_filter_wormhole_systems_by_class(
    test_client: AsyncClient,
    test_state: IntegrationTestState,  # noqa: ARG001
) -> None:
    """Test filtering wormhole systems by class."""
    # Filter by C3
    response = await test_client.get("/reference/systems?class=3")
    assert response.status_code == 200

    data = response.json()
    systems = _flatten_systems(data)

    # All returned systems should be C3
    for system in systems:
        assert system["system_class"] == 3
        assert system["class_name"] == "C3"

    # Should include J123456 and J345678 (both C3)
    system_ids = {s["id"] for s in systems}
    assert J123456_SYSTEM_ID in system_ids
    assert J345678_SYSTEM_ID in system_ids
    # Should not include J234567 (C5)
    assert J234567_SYSTEM_ID not in system_ids


@pytest.mark.order(731)
async def test_filter_wormhole_systems_by_effect(
    test_client: AsyncClient,
    test_state: IntegrationTestState,  # noqa: ARG001
) -> None:
    """Test filtering wormhole systems by effect."""
    # Filter by Black Hole effect (id=1)
    response = await test_client.get("/reference/systems?effect=1")
    assert response.status_code == 200

    data = response.json()
    systems = _flatten_systems(data)

    # All returned systems should have Black Hole effect
    for system in systems:
        assert system["effect_id"] == 1
        assert system["effect_name"] == "Black Hole"

    # Should include J123456
    system_ids = {s["id"] for s in systems}
    assert J123456_SYSTEM_ID in system_ids


@pytest.mark.order(732)
async def test_filter_wormhole_systems_by_static(
    test_client: AsyncClient,
    test_state: IntegrationTestState,  # noqa: ARG001
) -> None:
    """Test filtering wormhole systems by static target class."""
    # Filter by systems with a static leading to C5 (target_class=5)
    # J234567 has N944 static which leads to C5
    response = await test_client.get("/reference/systems?static=5")
    assert response.status_code == 200

    data = response.json()
    systems = _flatten_systems(data)

    # All returned systems should have a static with target_class 5
    for system in systems:
        target_classes = {s["target_class"] for s in system["statics"]}
        assert 5 in target_classes

    # Should include J234567
    system_ids = {s["id"] for s in systems}
    assert J234567_SYSTEM_ID in system_ids


@pytest.mark.order(733)
async def test_filter_wormhole_systems_combined_filters(
    test_client: AsyncClient,
    test_state: IntegrationTestState,  # noqa: ARG001
) -> None:
    """Test combining multiple filters."""
    # Filter by C3 class AND Black Hole effect
    response = await test_client.get("/reference/systems?class=3&effect=1")
    assert response.status_code == 200

    data = response.json()
    systems = _flatten_systems(data)

    # All returned systems should match both filters
    for system in systems:
        assert system["system_class"] == 3
        assert system["effect_id"] == 1

    # Should include J123456 (C3 with Black Hole)
    system_ids = {s["id"] for s in systems}
    assert J123456_SYSTEM_ID in system_ids
    # Should not include J345678 (C3 but no effect)
    assert J345678_SYSTEM_ID not in system_ids


@pytest.mark.order(734)
async def test_filter_wormhole_systems_no_results(
    test_client: AsyncClient,
    test_state: IntegrationTestState,  # noqa: ARG001
) -> None:
    """Test filtering that returns no results."""
    # Filter by C6 class (no C6 systems in preseed)
    response = await test_client.get("/reference/systems?class=6")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, dict)
    assert data["regions"] == []
    assert data["total_systems"] == 0


@pytest.mark.order(735)
async def test_filter_wormhole_systems_by_shattered(
    test_client: AsyncClient,
    test_state: IntegrationTestState,  # noqa: ARG001
) -> None:
    """Test filtering wormhole systems by shattered status."""
    # Filter for non-shattered systems
    response = await test_client.get("/reference/systems?shattered=false")
    assert response.status_code == 200

    data = response.json()
    systems = _flatten_systems(data)

    # All returned systems should not be shattered
    for system in systems:
        assert system["shattered"] is False

    # Our test systems (J123456, J234567, J345678) should be non-shattered
    # since their names don't start with J0 and they're not C13/drifter class
    system_ids = {s["id"] for s in systems}
    assert J123456_SYSTEM_ID in system_ids
    assert J234567_SYSTEM_ID in system_ids
    assert J345678_SYSTEM_ID in system_ids
