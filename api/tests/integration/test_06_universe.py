"""Universe/System details integration tests.

These tests verify the system details endpoint which returns
information about solar systems including planet/moon counts
and neighbouring systems.

Note: test_state fixture is required as a dependency to ensure authentication
runs first (via pytest-order), even though it's not directly used in these tests.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.factories.static_data import (
    HED_GP_SYSTEM_ID,
    J123456_SYSTEM_ID,
    JITA_SYSTEM_ID,
)
from tests.integration.conftest import IntegrationTestState

# =============================================================================
# System Details Tests - Valid Systems
# =============================================================================


@pytest.mark.order(600)
async def test_get_system_details_kspace(
    test_client: AsyncClient,
    test_state: IntegrationTestState,  # noqa: ARG001
) -> None:
    """Test getting system details for a k-space system (Jita)."""
    response = await test_client.get(f"/universe/systems/{JITA_SYSTEM_ID}/details")
    assert response.status_code == 200, f"Failed to get system details: {response.text}"

    data = response.json()

    # Verify required fields are present
    assert data["id"] == JITA_SYSTEM_ID
    assert data["name"] == "Jita"
    assert "radius" in data
    assert "planet_count" in data
    assert "moon_count" in data
    assert "station_count" in data
    assert "neighbours" in data

    # Verify types
    assert isinstance(data["planet_count"], int)
    assert isinstance(data["moon_count"], int)
    assert isinstance(data["station_count"], int)
    assert isinstance(data["neighbours"], list)


@pytest.mark.order(601)
async def test_get_system_details_wspace(
    test_client: AsyncClient,
    test_state: IntegrationTestState,  # noqa: ARG001
) -> None:
    """Test getting system details for a w-space system (J123456)."""
    response = await test_client.get(f"/universe/systems/{J123456_SYSTEM_ID}/details")
    assert response.status_code == 200, f"Failed to get system details: {response.text}"

    data = response.json()

    # Verify required fields
    assert data["id"] == J123456_SYSTEM_ID
    assert data["name"] == "J123456"
    assert "planet_count" in data
    assert "moon_count" in data

    # W-space systems have no NPC stations
    assert data["station_count"] == 0

    # W-space systems have no stargate neighbours
    assert data["neighbours"] == []


@pytest.mark.order(602)
async def test_get_system_details_nullsec(
    test_client: AsyncClient,
    test_state: IntegrationTestState,  # noqa: ARG001
) -> None:
    """Test getting system details for a null-sec system (HED-GP)."""
    response = await test_client.get(f"/universe/systems/{HED_GP_SYSTEM_ID}/details")
    assert response.status_code == 200, f"Failed to get system details: {response.text}"

    data = response.json()

    # Verify required fields
    assert data["id"] == HED_GP_SYSTEM_ID
    assert data["name"] == "HED-GP"
    assert "planet_count" in data
    assert "moon_count" in data
    assert "station_count" in data
    assert "neighbours" in data

    # Null-sec systems should have stargate neighbours
    # HED-GP is a famous entry system so it should have neighbours
    assert isinstance(data["neighbours"], list)


# =============================================================================
# System Details Tests - Error Cases
# =============================================================================


@pytest.mark.order(610)
async def test_get_system_details_not_found(
    test_client: AsyncClient,
    test_state: IntegrationTestState,  # noqa: ARG001
) -> None:
    """Test that non-existent system returns 404."""
    non_existent_system_id = 99999999
    response = await test_client.get(f"/universe/systems/{non_existent_system_id}/details")
    assert response.status_code == 404


@pytest.mark.order(611)
async def test_get_system_details_invalid_id(
    test_client: AsyncClient,
    test_state: IntegrationTestState,  # noqa: ARG001
) -> None:
    """Test that invalid system ID format returns 404.

    Note: Litestar's path parameter validation returns 404 for type mismatches,
    treating them as "path not found" rather than "bad request".
    """
    response = await test_client.get("/universe/systems/not-a-number/details")
    assert response.status_code == 404
