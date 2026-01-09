"""Test 05: Node updates.

Tests updating node position and locked status.

Note: SSE event verification is disabled because the test app uses an in-memory
channels backend while the EventCollector uses Valkey pub/sub.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from litestar.testing import AsyncTestClient

    from tests.integration.conftest import TestState

from tests.integration.conftest import set_auth


class TestNodeUpdates:
    """Test updating nodes on maps."""

    @pytest.mark.order(16)
    async def test_update_node_position(
        self,
        test_client: AsyncTestClient,
        test_state: TestState,
    ) -> None:
        """Update a node's position."""
        await set_auth(test_client, test_state)

        node_id = test_state.node_ids[0]  # Jita node

        response = await test_client.patch(
            f"/maps/{test_state.map_id}/nodes/{node_id}/position",
            json={
                "pos_x": 150.0,
                "pos_y": 150.0,
            },
        )

        assert response.status_code == 200, f"Failed to update node: {response.text}"

        data = response.json()
        assert data["node_id"] == str(node_id)

    @pytest.mark.order(17)
    async def test_lock_node(
        self,
        test_client: AsyncTestClient,
        test_state: TestState,
    ) -> None:
        """Lock a node to prevent position changes."""
        await set_auth(test_client, test_state)

        node_id = test_state.node_ids[0]  # Jita node

        response = await test_client.patch(
            f"/maps/{test_state.map_id}/nodes/{node_id}/locked",
            json={"locked": True},
        )

        assert response.status_code == 200, f"Failed to lock node: {response.text}"

    @pytest.mark.order(18)
    async def test_locked_node_rejects_position_update(
        self,
        test_client: AsyncTestClient,
        test_state: TestState,
    ) -> None:
        """Verify that locked nodes reject position updates."""
        await set_auth(test_client, test_state)

        node_id = test_state.node_ids[0]  # Jita node (locked)

        response = await test_client.patch(
            f"/maps/{test_state.map_id}/nodes/{node_id}/position",
            json={
                "pos_x": 200.0,
                "pos_y": 200.0,
            },
        )

        # Should fail with 409 CONFLICT
        assert response.status_code == 409, f"Expected 409 but got: {response.status_code}"

    @pytest.mark.order(19)
    async def test_unlock_node(
        self,
        test_client: AsyncTestClient,
        test_state: TestState,
    ) -> None:
        """Unlock a node to allow position changes again."""
        await set_auth(test_client, test_state)

        node_id = test_state.node_ids[0]  # Jita node

        response = await test_client.patch(
            f"/maps/{test_state.map_id}/nodes/{node_id}/locked",
            json={"locked": False},
        )

        assert response.status_code == 200
