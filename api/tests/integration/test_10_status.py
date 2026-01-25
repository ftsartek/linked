"""Status endpoint integration tests.

These tests verify the EVE server status endpoint which provides
Tranquility server status without requiring authentication.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.integration.conftest import IntegrationTestState


@pytest.mark.order(1000)
async def test_get_eve_status(
    test_client: AsyncClient,
    test_state: IntegrationTestState,  # noqa: ARG001
) -> None:
    """Test getting EVE server status returns expected structure."""
    response = await test_client.get("/status/eve")
    assert response.status_code == 200, f"Failed to get EVE status: {response.text}"

    data = response.json()

    # Verify required fields
    assert "online" in data
    assert "vip" in data
    assert "players" in data

    # Verify types
    assert isinstance(data["online"], bool)
    assert isinstance(data["vip"], bool)
    assert data["players"] is None or isinstance(data["players"], int)

    # Mock ESI client returns online with 12345 players
    assert data["online"] is True
    assert data["vip"] is False
    assert data["players"] == 12345


@pytest.mark.order(1001)
async def test_get_eve_status_unauthenticated(
    unauthenticated_client: AsyncClient,
) -> None:
    """Test that getting EVE status works without authentication."""
    response = await unauthenticated_client.get("/status/eve")
    assert response.status_code == 200, f"Public endpoint should not require auth: {response.text}"

    data = response.json()
    assert "online" in data
    assert "vip" in data
    assert "players" in data
