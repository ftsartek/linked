"""Test 04: Link creation.

Tests creating links between nodes.

Note: SSE event verification is disabled because the test app uses an in-memory
channels backend while the EventCollector uses Valkey pub/sub.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

import pytest

if TYPE_CHECKING:
    from litestar.testing import AsyncTestClient

    from tests.integration.conftest import TestState

from tests.integration.conftest import set_auth


class TestLinkCreation:
    """Test creating links between nodes."""

    @pytest.mark.order(13)
    async def test_create_link(
        self,
        test_client: AsyncTestClient,
        test_state: TestState,
    ) -> None:
        """Create a link between Jita and J123456 nodes with K162."""
        await set_auth(test_client, test_state)

        # Jita is first node, J123456 is second
        source_node_id = test_state.node_ids[0]
        target_node_id = test_state.node_ids[1]

        response = await test_client.post(
            f"/maps/{test_state.map_id}/links",
            json={
                "source_node_id": str(source_node_id),
                "target_node_id": str(target_node_id),
                "wormhole_id": test_state.k162_wormhole_id,
            },
        )

        assert response.status_code == 201, f"Failed to create link: {response.text}"

        data = response.json()
        assert "link_id" in data
        link_id = UUID(data["link_id"])
        test_state.link_ids.append(link_id)

    @pytest.mark.order(14)
    async def test_get_map_links(
        self,
        test_client: AsyncTestClient,
        test_state: TestState,
    ) -> None:
        """Verify the link appears when loading the map."""
        await set_auth(test_client, test_state)

        response = await test_client.get(f"/maps/{test_state.map_id}")

        assert response.status_code == 200

        data = response.json()
        assert len(data["links"]) == 1

        link = data["links"][0]
        assert link["wormhole_code"] == "K162"
        assert link["wormhole_lifetime"] == 24.0  # K162 has 24hr lifetime
        assert link["lifetime_status"] == "stable"

    @pytest.mark.order(15)
    async def test_duplicate_link_rejected(
        self,
        test_client: AsyncTestClient,
        test_state: TestState,
    ) -> None:
        """Test that creating a duplicate link between same nodes is rejected."""
        await set_auth(test_client, test_state)

        source_node_id = test_state.node_ids[0]
        target_node_id = test_state.node_ids[1]

        # Try to create another link between the same nodes
        response = await test_client.post(
            f"/maps/{test_state.map_id}/links",
            json={
                "source_node_id": str(source_node_id),
                "target_node_id": str(target_node_id),
                "wormhole_id": test_state.k162_wormhole_id,
            },
        )

        # Should fail with conflict or bad request error (not 500 - that would indicate unhandled error)
        assert response.status_code in (400, 409), f"Expected 400 or 409 but got: {response.status_code}"
