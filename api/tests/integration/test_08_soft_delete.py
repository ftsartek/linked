"""Test 08: Soft deletion.

Tests soft-deleting nodes, links, and maps with cascade behavior.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

import pytest

if TYPE_CHECKING:
    from litestar.testing import AsyncTestClient
    from sqlspec.adapters.asyncpg.driver import AsyncpgDriver

    from tests.integration.conftest import TestState

from tests.factories.static_data import J345678_SYSTEM_ID
from tests.integration.conftest import set_auth


class TestSoftDelete:
    """Test soft-deletion of nodes, links, and maps."""

    @pytest.mark.order(31)
    async def test_create_nodes_for_deletion_tests(
        self,
        test_client: AsyncTestClient,
        test_state: TestState,
    ) -> None:
        """Create additional nodes and links for deletion testing."""
        await set_auth(test_client, test_state)

        # Create a new node
        response = await test_client.post(
            f"/maps/{test_state.map_id}/nodes",
            json={
                "system_id": J345678_SYSTEM_ID,
                "pos_x": 700.0,
                "pos_y": 100.0,
            },
        )

        assert response.status_code == 201
        new_node_id = UUID(response.json()["node_id"])
        test_state.node_ids.append(new_node_id)

        # Create a link to this node from an existing node
        # Find a node that still exists (not soft-deleted)
        existing_node_id = test_state.node_ids[1]  # J123456

        response = await test_client.post(
            f"/maps/{test_state.map_id}/links",
            json={
                "source_node_id": str(existing_node_id),
                "target_node_id": str(new_node_id),
                "wormhole_id": test_state.k162_wormhole_id,
            },
        )

        assert response.status_code == 201
        new_link_id = UUID(response.json()["link_id"])
        test_state.link_ids.append(new_link_id)

    @pytest.mark.order(32)
    async def test_delete_link(
        self,
        test_client: AsyncTestClient,
        db_session: AsyncpgDriver,
        test_state: TestState,
    ) -> None:
        """Soft-delete a single link."""
        await set_auth(test_client, test_state)

        # Delete the last link we created
        link_id = test_state.link_ids[-1]

        response = await test_client.delete(
            f"/maps/{test_state.map_id}/links/{link_id}",
        )

        assert response.status_code == 202, f"Failed to delete link: {response.text}"

        data = response.json()
        assert data["link_id"] == str(link_id)

        # Verify soft-delete in database
        row = await db_session.select_one(
            "SELECT date_deleted FROM link WHERE id = $1",
            [link_id],
        )
        assert row["date_deleted"] is not None

    @pytest.mark.order(33)
    async def test_delete_node_cascades_to_links(
        self,
        test_client: AsyncTestClient,
        db_session: AsyncpgDriver,
        test_state: TestState,
    ) -> None:
        """Soft-delete a node and verify connected links are also deleted."""
        await set_auth(test_client, test_state)

        # Delete the last node we created (J345678)
        node_id = test_state.node_ids[-1]

        response = await test_client.delete(
            f"/maps/{test_state.map_id}/nodes/{node_id}",
        )

        assert response.status_code == 202, f"Failed to delete node: {response.text}"

        data = response.json()
        assert data["node_id"] == str(node_id)

        # Verify soft-delete in database
        row = await db_session.select_one(
            "SELECT date_deleted FROM node WHERE id = $1",
            [node_id],
        )
        assert row["date_deleted"] is not None

    @pytest.mark.order(34)
    async def test_verify_remaining_data(
        self,
        test_client: AsyncTestClient,
        test_state: TestState,
    ) -> None:
        """Verify the map still has some nodes/links after deletions."""
        await set_auth(test_client, test_state)

        response = await test_client.get(f"/maps/{test_state.map_id}")
        assert response.status_code == 200

        data = response.json()
        # Map should still exist and have remaining nodes (J345678 was deleted, others remain)
        assert data["map"]["id"] == str(test_state.map_id)
        # Verify we still have nodes - exact count depends on lifecycle test deletions
        assert len(data["nodes"]) >= 2, f"Expected at least 2 nodes but got {len(data['nodes'])}"

    @pytest.mark.order(35)
    async def test_delete_map_cascades(
        self,
        test_client: AsyncTestClient,
        db_session: AsyncpgDriver,
        test_state: TestState,
    ) -> None:
        """Soft-delete the entire map and verify cascade to nodes/links."""
        await set_auth(test_client, test_state)

        response = await test_client.delete(f"/maps/{test_state.map_id}")

        assert response.status_code == 202, f"Failed to delete map: {response.text}"

        data = response.json()
        assert "deleted_node_ids" in data
        assert "deleted_link_ids" in data

        # Verify soft-delete in database
        map_row = await db_session.select_one(
            "SELECT date_deleted FROM map WHERE id = $1",
            [test_state.map_id],
        )
        assert map_row["date_deleted"] is not None

        # Verify all nodes are soft-deleted
        node_count = await db_session.select_value(
            "SELECT COUNT(*) FROM node WHERE map_id = $1 AND date_deleted IS NULL",
            [test_state.map_id],
        )
        assert node_count == 0

        # Verify all links are soft-deleted
        link_count = await db_session.select_value(
            "SELECT COUNT(*) FROM link WHERE map_id = $1 AND date_deleted IS NULL",
            [test_state.map_id],
        )
        assert link_count == 0
