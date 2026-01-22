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
