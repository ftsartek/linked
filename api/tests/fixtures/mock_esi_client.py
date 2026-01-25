"""Mock ESI client for testing.

Provides a mock implementation of ESIClient that returns test data
without making real HTTP requests.
"""

from __future__ import annotations

from esi_client import ESIClient
from esi_client.models import ESIAlliance, ESICharacter, ESICorporation, ServerStatus
from tests.factories.static_data import (
    AMARR_SYSTEM_ID,
    DODIXIE_SYSTEM_ID,
    HED_GP_SYSTEM_ID,
    HEK_SYSTEM_ID,
    JITA_SYSTEM_ID,
    PERIMETER_SYSTEM_ID,
    PR_8CA_SYSTEM_ID,
    RENS_SYSTEM_ID,
    TEST_ALLIANCE_ID,
    TEST_CHARACTER_ID,
    TEST_CHARACTER_NAME,
    TEST_CORPORATION_ID,
)

# Mock route data between k-space systems
# These are simplified routes for testing - not real EVE routes
MOCK_ROUTES: dict[tuple[int, int], list[int]] = {
    # Jita to other trade hubs (simplified)
    (JITA_SYSTEM_ID, AMARR_SYSTEM_ID): [JITA_SYSTEM_ID, 30000139, 30000138, AMARR_SYSTEM_ID],
    (JITA_SYSTEM_ID, DODIXIE_SYSTEM_ID): [JITA_SYSTEM_ID, 30000140, DODIXIE_SYSTEM_ID],
    (JITA_SYSTEM_ID, RENS_SYSTEM_ID): [JITA_SYSTEM_ID, 30000141, RENS_SYSTEM_ID],
    (JITA_SYSTEM_ID, HEK_SYSTEM_ID): [JITA_SYSTEM_ID, 30000143, HEK_SYSTEM_ID],
    (JITA_SYSTEM_ID, PERIMETER_SYSTEM_ID): [JITA_SYSTEM_ID, PERIMETER_SYSTEM_ID],
    # Jita to null-sec
    (JITA_SYSTEM_ID, HED_GP_SYSTEM_ID): [JITA_SYSTEM_ID, 30000145, 30000146, HED_GP_SYSTEM_ID],
    (JITA_SYSTEM_ID, PR_8CA_SYSTEM_ID): [JITA_SYSTEM_ID, 30000145, 30000146, HED_GP_SYSTEM_ID, PR_8CA_SYSTEM_ID],
    # Perimeter routes
    (PERIMETER_SYSTEM_ID, JITA_SYSTEM_ID): [PERIMETER_SYSTEM_ID, JITA_SYSTEM_ID],
    (PERIMETER_SYSTEM_ID, AMARR_SYSTEM_ID): [PERIMETER_SYSTEM_ID, JITA_SYSTEM_ID, 30000139, 30000138, AMARR_SYSTEM_ID],
    # HED-GP routes
    (HED_GP_SYSTEM_ID, JITA_SYSTEM_ID): [HED_GP_SYSTEM_ID, 30000146, 30000145, JITA_SYSTEM_ID],
    (HED_GP_SYSTEM_ID, PR_8CA_SYSTEM_ID): [HED_GP_SYSTEM_ID, PR_8CA_SYSTEM_ID],
    # Amarr routes
    (AMARR_SYSTEM_ID, JITA_SYSTEM_ID): [AMARR_SYSTEM_ID, 30000138, 30000139, JITA_SYSTEM_ID],
}


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

    async def get_server_status(self) -> ServerStatus:
        """Return mock server status data."""
        return ServerStatus(
            players=12345,
            server_version="1234567",
            start_time="2026-01-25T11:00:00Z",
            vip=None,
        )

    async def get_route(
        self,
        origin: int,
        destination: int,
        flag: str = "shortest",  # noqa: ARG002
    ) -> list[int]:
        """Return mock route data.

        Uses predefined routes from MOCK_ROUTES dict.
        For unknown routes, generates a simple direct route.
        """
        # Same system - return single element
        if origin == destination:
            return [origin]

        # Check for predefined route
        route_key = (origin, destination)
        if route_key in MOCK_ROUTES:
            return MOCK_ROUTES[route_key]

        # Check for reverse route
        reverse_key = (destination, origin)
        if reverse_key in MOCK_ROUTES:
            return list(reversed(MOCK_ROUTES[reverse_key]))

        # Generate a simple mock route for unknown pairs
        # This simulates a 3-jump route through fictional intermediates
        return [origin, origin + 1, destination]


async def provide_mock_esi_client() -> MockESIClient:
    """Provide mock ESI client for dependency injection in tests."""
    return MockESIClient()
