"""Mock ESI client for testing.

Provides a mock implementation of ESIClient that returns test data
without making real HTTP requests.
"""

from __future__ import annotations

from esi_client import ESIClient
from esi_client.models import ESIAlliance, ESICharacter, ESICorporation
from tests.factories.static_data import (
    TEST_ALLIANCE_ID,
    TEST_CHARACTER_ID,
    TEST_CHARACTER_NAME,
    TEST_CORPORATION_ID,
)


class MockESIClient(ESIClient):
    """Mock ESI client - returns test data without HTTP calls."""

    def __init__(self) -> None:
        """Initialize without settings - no HTTP client needed."""
        pass

    async def __aenter__(self) -> MockESIClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        pass

    async def get_character(self, character_id: int) -> ESICharacter:
        """Return mock character data."""
        # Return appropriate test data based on character ID
        if character_id == TEST_CHARACTER_ID:
            return ESICharacter(
                name=TEST_CHARACTER_NAME,
                corporation_id=TEST_CORPORATION_ID,
                alliance_id=TEST_ALLIANCE_ID,
            )
        # Default fallback for unknown characters
        return ESICharacter(
            name=f"Character {character_id}",
            corporation_id=TEST_CORPORATION_ID,
            alliance_id=TEST_ALLIANCE_ID,
        )

    async def get_corporation(self, corporation_id: int) -> ESICorporation:
        """Return mock corporation data."""
        if corporation_id == TEST_CORPORATION_ID:
            return ESICorporation(
                name="Test Corporation",
                ticker="TEST",
                alliance_id=TEST_ALLIANCE_ID,
                member_count=100,
            )
        # Default fallback
        return ESICorporation(
            name=f"Corporation {corporation_id}",
            ticker="CORP",
            alliance_id=None,
            member_count=1,
        )

    async def get_alliance(self, alliance_id: int) -> ESIAlliance:
        """Return mock alliance data."""
        if alliance_id == TEST_ALLIANCE_ID:
            return ESIAlliance(
                name="Test Alliance",
                ticker="TSTA",
            )
        # Default fallback
        return ESIAlliance(
            name=f"Alliance {alliance_id}",
            ticker="ALLY",
        )


async def provide_mock_esi_client() -> MockESIClient:
    """Provide mock ESI client for dependency injection in tests."""
    return MockESIClient()
