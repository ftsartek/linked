from __future__ import annotations

from litestar import Controller, Request, Response, get
from litestar.di import Provide
from litestar.exceptions import ClientException, NotAuthorizedException, NotFoundException
from litestar.status_codes import HTTP_200_OK

from api.auth.guards import require_auth
from routes.universe.dependencies import (
    LocalSearchResponse,
    SystemSearchResponse,
    SystemSearchResponseDTO,
    UniverseSearchResponse,
    WormholeSearchResponse,
)
from routes.universe.service import (
    UniverseService,
    provide_universe_service,
    provide_universe_service_with_auth,
)
from services.encryption import provide_encryption_service
from services.image_cache import ImageCacheService, provide_image_cache_service

# Session key for cached ESI access token
ESI_ACCESS_TOKEN_KEY = "esi_access_token"

# Valid categories for entity search
VALID_CATEGORIES = {"character", "corporation", "alliance"}


class UniverseController(Controller):
    """Universe search endpoints."""

    path = "/universe"
    guards = [require_auth]
    dependencies = {
        "universe_service": Provide(provide_universe_service),
        "universe_service_auth": Provide(provide_universe_service_with_auth),
        "encryption_service": Provide(provide_encryption_service),
        "image_cache_service": Provide(provide_image_cache_service),
    }

    @get("/systems", return_dto=SystemSearchResponseDTO)
    async def search_systems(
        self,
        universe_service: UniverseService,
        q: str,
    ) -> SystemSearchResponse:
        """Search systems by name."""
        systems = await universe_service.search_systems(q)
        return SystemSearchResponse(systems=systems)

    @get("/wormholes")
    async def search_wormholes(
        self,
        universe_service: UniverseService,
        q: str,
        target_class: int | None = None,
        source: int | None = None,
    ) -> WormholeSearchResponse:
        """Search wormholes by code with optional target_class/source filters."""
        wormholes = await universe_service.search_wormholes(q, target_class, source)
        return WormholeSearchResponse(wormholes=wormholes)

    @get("/systems/unidentified", return_dto=SystemSearchResponseDTO)
    async def list_unidentified_systems(
        self,
        universe_service: UniverseService,
    ) -> SystemSearchResponse:
        """List all unidentified placeholder systems."""
        systems = await universe_service.list_unidentified_systems()
        return SystemSearchResponse(systems=systems)

    @get("/search")
    async def search_entities(
        self,
        request: Request,
        universe_service_auth: UniverseService,
        q: str,
        categories: str = "character,corporation,alliance",
    ) -> UniverseSearchResponse:
        """Search for characters, corporations, and alliances by name.

        Uses EVE ESI authenticated search which supports substring matching.

        Args:
            q: Search query (minimum 3 characters)
            categories: Comma-separated list of categories to search
                       (character, corporation, alliance)

        Returns:
            Matching entities grouped by category
        """
        # Validate query length
        if len(q) < 3:
            raise ClientException("Search query must be at least 3 characters")

        # Parse and validate categories
        requested_categories = [c.strip() for c in categories.split(",")]
        invalid = set(requested_categories) - VALID_CATEGORIES
        if invalid:
            raise ClientException(f"Invalid categories: {', '.join(invalid)}")

        character_id = request.user.character_id

        # Get cached access token from session
        cached_token = request.session.get(ESI_ACCESS_TOKEN_KEY)

        try:
            # Get or refresh access token
            access_token, was_refreshed = await universe_service_auth.get_access_token(
                character_id,
                cached_token,
            )

            # Cache the new token if it was refreshed
            if was_refreshed:
                request.session[ESI_ACCESS_TOKEN_KEY] = access_token

            # Perform the search
            results = await universe_service_auth.search_entities(
                character_id=character_id,
                query=q,
                categories=requested_categories,
                access_token=access_token,
            )

            return UniverseSearchResponse(
                characters=results["characters"],
                corporations=results["corporations"],
                alliances=results["alliances"],
            )

        except ValueError as e:
            raise NotAuthorizedException(str(e)) from e

    @get("/search/local")
    async def search_local_entities(
        self,
        universe_service: UniverseService,
        q: str,
    ) -> LocalSearchResponse:
        """Search local database for characters, corporations, and alliances.

        Only returns entities that exist in the local database, suitable for
        map sharing where foreign key constraints require local entities.

        Results are sorted by match quality:
        1. Exact matches
        2. Prefix matches
        3. Trigram similarity matches

        Args:
            q: Search query (minimum 3 characters)

        Returns:
            Flat list of matching entities with type information
        """
        if len(q) < 3:
            raise ClientException("Search query must be at least 3 characters")

        results = await universe_service.search_local_entities(q)
        return LocalSearchResponse(results=results)

    @get("/images/{entity_type:str}/{entity_id:int}", guards=[])
    async def get_entity_image(
        self,
        image_cache_service: ImageCacheService,
        entity_type: str,
        entity_id: int,
        size: int = 64,
    ) -> Response[bytes]:
        """Get an EVE entity image (character portrait, corp/alliance logo).

        Images are cached locally with a 3-day TTL.

        Args:
            entity_type: Type of entity (character, corporation, alliance)
            entity_id: EVE entity ID
            size: Image size (32, 64, 128, 256, 512, 1024). Default: 64

        Returns:
            PNG image data
        """
        if entity_type not in VALID_CATEGORIES:
            raise NotFoundException(f"Invalid entity type: {entity_type}")

        result = await image_cache_service.get_image(entity_type, entity_id, size)

        if result is None:
            raise NotFoundException(f"Image not found for {entity_type} {entity_id}")

        image_data, content_type = result

        return Response(
            content=image_data,
            status_code=HTTP_200_OK,
            media_type=content_type,
            headers={
                "Cache-Control": "public, max-age=259200",  # 3 days
            },
        )
