"""Test 06: Link updates.

Tests updating link properties like lifetime status and mass usage.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from litestar.testing import AsyncTestClient

    from tests.integration.conftest import TestState

from tests.integration.conftest import set_auth


class TestLinkUpdates:
    """Test updating links on maps."""

    @pytest.mark.order(20)
    async def test_update_link_lifetime_status(
        self,
        test_client: AsyncTestClient,
        test_state: TestState,
    ) -> None:
        """Update a link's lifetime status."""
        await set_auth(test_client, test_state)

        link_id = test_state.link_ids[0]

        response = await test_client.patch(
            f"/maps/{test_state.map_id}/links/{link_id}",
            json={
                "lifetime_status": "aging",
            },
        )

        assert response.status_code == 200, f"Failed to update link: {response.text}"

        data = response.json()
        assert data["link_id"] == str(link_id)

    @pytest.mark.order(21)
    async def test_update_link_mass_usage(
        self,
        test_client: AsyncTestClient,
        test_state: TestState,
    ) -> None:
        """Update a link's mass usage."""
        await set_auth(test_client, test_state)

        link_id = test_state.link_ids[0]

        response = await test_client.patch(
            f"/maps/{test_state.map_id}/links/{link_id}",
            json={
                "mass_usage": 50,  # 50% mass used
            },
        )

        assert response.status_code == 200, f"Failed to update link: {response.text}"

        data = response.json()
        assert data["link_id"] == str(link_id)

    @pytest.mark.order(22)
    async def test_set_link_type_from_node(
        self,
        test_client: AsyncTestClient,
        test_state: TestState,
    ) -> None:
        """Set wormhole type on a link from a specific node."""
        await set_auth(test_client, test_state)

        link_id = test_state.link_ids[0]
        from_node_id = test_state.node_ids[1]  # J123456 node

        response = await test_client.patch(
            f"/maps/{test_state.map_id}/links/{link_id}/set-type",
            json={
                "from_node_id": str(from_node_id),
                "wormhole_id": test_state.k162_wormhole_id,
            },
        )

        assert response.status_code == 200, f"Failed to set link type: {response.text}"

        data = response.json()
        assert data["link_id"] == str(link_id)

    @pytest.mark.order(23)
    async def test_reset_link_status_for_lifecycle_tests(
        self,
        test_client: AsyncTestClient,
        test_state: TestState,
    ) -> None:
        """Reset link to stable status for lifecycle tests."""
        await set_auth(test_client, test_state)

        link_id = test_state.link_ids[0]

        response = await test_client.patch(
            f"/maps/{test_state.map_id}/links/{link_id}",
            json={
                "lifetime_status": "stable",
                "mass_usage": 0,
            },
        )

        assert response.status_code == 200
