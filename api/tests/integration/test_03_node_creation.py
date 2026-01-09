"""Test 03: Node creation.

Tests creating nodes on the map.

Note: SSE event verification is disabled because the test app uses an in-memory
channels backend while the EventCollector uses Valkey pub/sub. The HTTP API
functionality is the primary focus of these tests.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

import pytest

if TYPE_CHECKING:
    from litestar.testing import AsyncTestClient

    from tests.integration.conftest import TestState

from tests.factories.static_data import J123456_SYSTEM_ID, JITA_SYSTEM_ID
from tests.integration.conftest import set_auth


class TestNodeCreation:
    """Test creating nodes on maps."""

    @pytest.mark.order(9)
    async def test_create_jita_node(
        self,
        test_client: AsyncTestClient,
        test_state: TestState,
    ) -> None:
        """Create a node for Jita system."""
        await set_auth(test_client, test_state)

        response = await test_client.post(
            f"/maps/{test_state.map_id}/nodes",
            json={
                "system_id": JITA_SYSTEM_ID,
                "pos_x": 100.0,
                "pos_y": 100.0,
            },
        )

        assert response.status_code == 201, f"Failed to create node: {response.text}"

        data = response.json()
        assert "node_id" in data
        node_id = UUID(data["node_id"])
        test_state.node_ids.append(node_id)

    @pytest.mark.order(10)
    async def test_create_wormhole_node(
        self,
        test_client: AsyncTestClient,
        test_state: TestState,
    ) -> None:
        """Create a node for J123456 wormhole system."""
        await set_auth(test_client, test_state)

        response = await test_client.post(
            f"/maps/{test_state.map_id}/nodes",
            json={
                "system_id": J123456_SYSTEM_ID,
                "pos_x": 300.0,
                "pos_y": 100.0,
            },
        )

        assert response.status_code == 201, f"Failed to create node: {response.text}"

        data = response.json()
        node_id = UUID(data["node_id"])
        test_state.node_ids.append(node_id)

    @pytest.mark.order(11)
    async def test_get_map_nodes(
        self,
        test_client: AsyncTestClient,
        test_state: TestState,
    ) -> None:
        """Verify both nodes appear when loading the map."""
        await set_auth(test_client, test_state)

        response = await test_client.get(f"/maps/{test_state.map_id}")

        assert response.status_code == 200

        data = response.json()
        assert len(data["nodes"]) == 2

        # Verify we have both systems
        system_names = {node["system_name"] for node in data["nodes"]}
        assert "Jita" in system_names
        assert "J123456" in system_names

    @pytest.mark.order(12)
    async def test_duplicate_node_rejected(
        self,
        test_client: AsyncTestClient,
        test_state: TestState,
    ) -> None:
        """Test that creating a duplicate node for the same system is rejected."""
        await set_auth(test_client, test_state)

        # Try to create another Jita node
        response = await test_client.post(
            f"/maps/{test_state.map_id}/nodes",
            json={
                "system_id": JITA_SYSTEM_ID,
                "pos_x": 200.0,
                "pos_y": 200.0,
            },
        )

        # Should fail with conflict or bad request error (not 500 - that would indicate unhandled error)
        assert response.status_code in (400, 409), f"Expected 400 or 409 but got: {response.status_code}"
