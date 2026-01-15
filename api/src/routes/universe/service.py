from __future__ import annotations

from datetime import timedelta

from sqlspec import AsyncDriverAdapterBase

from database.models.refresh_token import SELECT_BY_CHARACTER_STMT, RefreshToken
from esi_client import ESIClient
from routes.universe.dependencies import (
    ClassMapping,
    EntitySearchResult,
    LocalEntitySearchResult,
    SystemSearchResult,
    WormholeSearchResult,
)
from routes.universe.queries import (
    LIST_UNIDENTIFIED_SYSTEMS,
    SEARCH_LOCAL_ENTITIES,
    SEARCH_SYSTEMS,
    SEARCH_WORMHOLES,
)
from services.encryption import EncryptionService
from services.eve_sso import EveSSOService

# Access token cache TTL (19 minutes, tokens valid for 20)
ACCESS_TOKEN_TTL = timedelta(seconds=1140)

# ESI category name mapping (our API uses plural, ESI uses singular)
CATEGORY_MAP = {
    "character": "character",
    "corporation": "corporation",
    "alliance": "alliance",
}


class UniverseService:
    """Universe search business logic."""

    def __init__(
        self,
        db_session: AsyncDriverAdapterBase,
        encryption_service: EncryptionService | None = None,
        sso_service: EveSSOService | None = None,
        esi_client: ESIClient | None = None,
    ) -> None:
        self.db_session = db_session
        self.encryption_service = encryption_service
        self.sso_service = sso_service
        self.esi_client = esi_client

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
        query: str | None,
        target_class: int | None = None,
        source_class: int | None = None,
    ) -> list[WormholeSearchResult]:
        """Search wormholes by code using trigram similarity with optional filters.

        Args:
            query: Wormhole code to search for (None or empty returns all matching filters)
            target_class: Filter by target system class
            source_class: Filter by source system class (includes K162 which can appear anywhere)
        """
        # Handle None/empty query - pass empty string for pattern matching bypass
        pattern = f"{query}%" if query else ""
        query_value = query or ""
        items = await self.db_session.select(
            SEARCH_WORMHOLES,
            pattern,
            query_value,
            target_class,
            source_class,
        )

        return [
            WormholeSearchResult(
                id=item["id"],
                code=item["code"],
                target=ClassMapping(item["target_class"]),
                sources=[ClassMapping(source) for source in item["sources"]] if item.get("sources") else [],
            )
            for item in items
        ]

    async def list_unidentified_systems(self) -> list[SystemSearchResult]:
        """List all unidentified placeholder systems."""
        return await self.db_session.select(
            LIST_UNIDENTIFIED_SYSTEMS,
            schema_type=SystemSearchResult,
        )

    async def search_local_entities(self, query: str) -> list[LocalEntitySearchResult]:
        """Search local database for characters, corporations, and alliances.

        Only returns entities that exist in the local database, suitable for
        map sharing where foreign key constraints require local entities.

        Results are sorted by match quality:
        1. Exact matches
        2. Prefix matches
        3. Trigram similarity matches
        """
        pattern = f"{query}%"
        return await self.db_session.select(
            SEARCH_LOCAL_ENTITIES,
            query,
            pattern,
            schema_type=LocalEntitySearchResult,
        )

    async def get_access_token(
        self,
        character_id: int,
        cached_token: str | None,
    ) -> tuple[str, bool]:
        """Get a valid access token for the character.

        Args:
            character_id: EVE character ID
            cached_token: Previously cached access token, if any

        Returns:
            Tuple of (access_token, was_refreshed) where was_refreshed indicates
            if a new token was obtained and should be cached.

        Raises:
            ValueError: If no refresh token found or refresh fails
        """
        if cached_token is not None:
            return cached_token, False

        if self.encryption_service is None or self.sso_service is None:
            msg = "Encryption and SSO services required for token refresh"
            raise ValueError(msg)

        # Fetch refresh token from database
        token_record = await self.db_session.select_one_or_none(
            SELECT_BY_CHARACTER_STMT,
            character_id,
            schema_type=RefreshToken,
        )
        if token_record is None or token_record.token is None:
            msg = "No refresh token found for character"
            raise ValueError(msg)

        # Decrypt and refresh
        refresh_token = self.encryption_service.decrypt(token_record.token)
        token_response = await self.sso_service.refresh_access_token(refresh_token)

        return token_response.access_token, True

    async def search_entities(
        self,
        character_id: int,
        query: str,
        categories: list[str],
        access_token: str,
    ) -> dict[str, list[EntitySearchResult]]:
        """Search for characters, corporations, and alliances via ESI.

        Args:
            character_id: EVE character ID to search as
            query: Search string (min 3 characters)
            categories: List of categories to search
            access_token: Valid ESI access token

        Returns:
            Dict mapping category names to lists of EntitySearchResult

        Raises:
            ValueError: If ESI client is not configured
        """
        if self.esi_client is None:
            msg = "ESI client required for entity search"
            raise ValueError(msg)

        async with self.esi_client as client:
            # Call ESI search
            search_result = await client.search(
                access_token=access_token,
                character_id=character_id,
                query=query,
                categories=categories,
            )

            # Collect all IDs to resolve
            all_ids: list[int] = []
            if search_result.character:
                all_ids.extend(search_result.character)
            if search_result.corporation:
                all_ids.extend(search_result.corporation)
            if search_result.alliance:
                all_ids.extend(search_result.alliance)

            if not all_ids:
                return {
                    "characters": [],
                    "corporations": [],
                    "alliances": [],
                }

            # Resolve IDs to names
            name_results = await client.resolve_ids_to_names(all_ids)

        # Build lookup by ID
        names_by_id = {r.id: r.name for r in name_results}

        # Build response grouped by category
        result: dict[str, list[EntitySearchResult]] = {
            "characters": [],
            "corporations": [],
            "alliances": [],
        }

        if search_result.character:
            result["characters"] = [
                EntitySearchResult(id=id_, name=names_by_id.get(id_, "Unknown")) for id_ in search_result.character
            ]
        if search_result.corporation:
            result["corporations"] = [
                EntitySearchResult(id=id_, name=names_by_id.get(id_, "Unknown")) for id_ in search_result.corporation
            ]
        if search_result.alliance:
            result["alliances"] = [
                EntitySearchResult(id=id_, name=names_by_id.get(id_, "Unknown")) for id_ in search_result.alliance
            ]

        return result


async def provide_universe_service(db_session: AsyncDriverAdapterBase) -> UniverseService:
    """Provide UniverseService with injected database session."""
    return UniverseService(db_session)


async def provide_universe_service_with_auth(
    db_session: AsyncDriverAdapterBase,
    encryption_service: EncryptionService,
    sso_service: EveSSOService,
    esi_client: ESIClient,
) -> UniverseService:
    """Provide UniverseService with auth dependencies for ESI search."""
    return UniverseService(db_session, encryption_service, sso_service, esi_client)
