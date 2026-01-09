"""Test 02: System and wormhole search.

Tests the universe search endpoints to find systems and wormhole types.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from litestar.testing import AsyncTestClient

    from tests.integration.conftest import TestState

from tests.factories.static_data import (
    J123456_SYSTEM_ID,
    JITA_SYSTEM_ID,
    K162_WORMHOLE_ID,
)
from tests.integration.conftest import set_auth


class TestSystemSearch:
    """Test searching for systems and wormhole types."""

    @pytest.mark.order(5)
    async def test_search_jita(
        self,
        test_client: AsyncTestClient,
        test_state: TestState,
    ) -> None:
        """Search for Jita system."""
        await set_auth(test_client, test_state)

        response = await test_client.get("/universe/systems", params={"q": "Jita"})

        assert response.status_code == 200

        data = response.json()
        assert "systems" in data, f"Expected 'systems' key in response: {data}"
        systems = data["systems"]
        assert len(systems) >= 1

        # Find Jita in the results
        jita = next((s for s in systems if s["name"] == "Jita"), None)
        assert jita is not None, f"Jita not found in results: {systems}"
        assert jita["id"] == JITA_SYSTEM_ID

    @pytest.mark.order(6)
    async def test_search_wormhole_system(
        self,
        test_client: AsyncTestClient,
        test_state: TestState,
    ) -> None:
        """Search for J123456 wormhole system."""
        await set_auth(test_client, test_state)

        response = await test_client.get("/universe/systems", params={"q": "J123456"})

        assert response.status_code == 200

        data = response.json()
        assert "systems" in data, f"Expected 'systems' key in response: {data}"
        systems = data["systems"]
        assert len(systems) >= 1

        j_system = systems[0]
        assert j_system["name"] == "J123456"
        assert j_system["id"] == J123456_SYSTEM_ID

    @pytest.mark.order(7)
    async def test_search_wormhole_types(
        self,
        test_client: AsyncTestClient,
        test_state: TestState,
    ) -> None:
        """Search for K162 wormhole type."""
        await set_auth(test_client, test_state)

        response = await test_client.get("/universe/wormholes", params={"q": "K162"})

        assert response.status_code == 200

        data = response.json()
        assert "wormholes" in data, f"Expected 'wormholes' key in response: {data}"
        wormholes = data["wormholes"]
        assert len(wormholes) >= 1

        k162 = wormholes[0]
        assert k162["code"] == "K162"
        assert k162["id"] == K162_WORMHOLE_ID

        # Store for later use
        test_state.k162_wormhole_id = k162["id"]

    @pytest.mark.order(8)
    async def test_search_partial_match(
        self,
        test_client: AsyncTestClient,
        test_state: TestState,
    ) -> None:
        """Test that partial matches work for system search."""
        await set_auth(test_client, test_state)

        # Search with partial name
        response = await test_client.get("/universe/systems", params={"q": "J12"})

        assert response.status_code == 200

        data = response.json()
        assert "systems" in data, f"Expected 'systems' key in response: {data}"
        systems = data["systems"]
        # Should find J123456
        assert any(s["name"] == "J123456" for s in systems)
