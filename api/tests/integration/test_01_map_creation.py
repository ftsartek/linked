"""Test 01: Map creation.

This is the first test in the sequence and sets up the user and map
that subsequent tests will use.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

import pytest

if TYPE_CHECKING:
    from litestar.testing import AsyncTestClient
    from sqlspec.adapters.asyncpg.driver import AsyncpgDriver

    from tests.integration.conftest import TestState

from tests.factories.user_data import create_test_user_with_character


class TestMapCreation:
    """Test creating maps via the HTTP API."""

    @pytest.mark.order(1)
    async def test_setup_user(
        self,
        db_session: AsyncpgDriver,
        test_state: TestState,
    ) -> None:
        """Create test user and character in the database."""
        user_id, character_id = await create_test_user_with_character(db_session)

        test_state.user_id = user_id
        test_state.character_id = character_id

        assert test_state.user_id is not None
        assert test_state.character_id is not None

    @pytest.mark.order(2)
    async def test_create_map(
        self,
        test_client: AsyncTestClient,
        test_state: TestState,
    ) -> None:
        """Create a new map via POST /maps/."""
        # Set up authenticated session
        await test_client.set_session_data(
            {
                "user_id": str(test_state.user_id),
                "character_id": test_state.character_id,
                "character_name": test_state.character_name,
            }
        )

        response = await test_client.post(
            "/maps/",
            json={
                "name": "Test Wormhole Map",
                "description": "A map for integration testing",
                "is_public": False,
            },
        )

        assert response.status_code == 201, f"Failed to create map: {response.text}"

        data = response.json()
        assert "id" in data
        assert data["name"] == "Test Wormhole Map"
        assert data["description"] == "A map for integration testing"

        test_state.map_id = UUID(data["id"])

    @pytest.mark.order(3)
    async def test_list_owned_maps(
        self,
        test_client: AsyncTestClient,
        test_state: TestState,
    ) -> None:
        """Verify the created map appears in the owned maps list."""
        await test_client.set_session_data(
            {
                "user_id": str(test_state.user_id),
                "character_id": test_state.character_id,
                "character_name": test_state.character_name,
            }
        )

        response = await test_client.get("/maps/owned")

        assert response.status_code == 200

        data = response.json()
        assert "maps" in data
        assert len(data["maps"]) == 1
        assert UUID(data["maps"][0]["id"]) == test_state.map_id
        assert data["maps"][0]["name"] == "Test Wormhole Map"

    @pytest.mark.order(4)
    async def test_load_map(
        self,
        test_client: AsyncTestClient,
        test_state: TestState,
    ) -> None:
        """Load the full map details via GET /maps/{map_id}."""
        await test_client.set_session_data(
            {
                "user_id": str(test_state.user_id),
                "character_id": test_state.character_id,
                "character_name": test_state.character_name,
            }
        )

        response = await test_client.get(f"/maps/{test_state.map_id}")

        assert response.status_code == 200

        data = response.json()
        assert "map" in data
        assert "nodes" in data
        assert "links" in data

        # Map should be empty initially
        assert len(data["nodes"]) == 0
        assert len(data["links"]) == 0

        # Owner should have edit access
        assert data["map"]["edit_access"] is True
