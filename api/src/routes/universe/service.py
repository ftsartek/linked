from __future__ import annotations

from sqlspec import AsyncDriverAdapterBase

from routes.universe.dependencies import (
    SystemSearchResult,
    WormholeSearchResult,
)
from routes.universe.queries import (
    SEARCH_SYSTEMS,
    SEARCH_WORMHOLES,
)


class UniverseService:
    """Universe search business logic."""

    def __init__(self, db_session: AsyncDriverAdapterBase) -> None:
        self.db_session = db_session

    async def search_systems(self, query: str) -> list[SystemSearchResult]:
        """Search systems by name using trigram similarity."""
        # Use ILIKE pattern for prefix matching, raw query for trigram
        pattern = f"{query}%"
        return await self.db_session.select(
            SEARCH_SYSTEMS,
            pattern,
            query,
            schema_type=SystemSearchResult,
        )

    async def search_wormholes(
        self,
        query: str,
        destination: str | None = None,
        source: str | None = None,
    ) -> list[WormholeSearchResult]:
        """Search wormholes by code using trigram similarity with optional filters."""
        pattern = f"{query}%"
        return await self.db_session.select(
            SEARCH_WORMHOLES,
            pattern,
            query,
            destination,
            source,
            schema_type=WormholeSearchResult,
        )


def provide_universe_service(db_session: AsyncDriverAdapterBase) -> UniverseService:
    """Provide UniverseService with injected database session."""
    return UniverseService(db_session)
