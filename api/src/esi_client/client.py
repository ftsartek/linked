"""ESI (EVE Swagger Interface) HTTP client.

This module provides an async HTTP client for interacting with EVE Online's
ESI API, with features including:

- ETag-based conditional caching for bandwidth efficiency
- Automatic retry with exponential backoff for transient failures
- Rate limit handling with Retry-After header support
- LRU cache eviction to bound memory usage
"""

from __future__ import annotations

import asyncio
import random
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from typing import TypeVar, cast

import httpx
import msgspec

from config import Settings

from .exceptions import ESIError, ESIForbiddenError, ESINotFoundError, ESIRateLimitError, ESIServerError
from .models import (
    Constellation,
    ESIAlliance,
    ESICharacter,
    ESICharacterLocation,
    ESICharacterOnline,
    ESICharacterShip,
    ESICorporation,
    ESINameResult,
    ESISearchResponse,
    ESIStructure,
    Region,
    ServerStatus,
    System,
    UniverseGroup,
    UniverseType,
)

T = TypeVar("T")

# ESI compatibility date - update periodically to opt into API changes
ESI_COMPATIBILITY_DATE = "2026-01-25"

# ETag cache configuration - limits memory usage for long-running instances
ETAG_CACHE_MAX_SIZE = 1000

# Retry configuration for transient failures (5xx, rate limits)
ESI_MAX_RETRIES = 3
ESI_BASE_DELAY = 1.0  # seconds
ESI_MAX_DELAY = 30.0  # seconds


def _wrap_http_error(e: httpx.HTTPStatusError, path: str) -> ESIError:
    """Wrap an httpx.HTTPStatusError in a domain-specific ESI exception."""
    status = e.response.status_code
    if status == 403:
        return ESIForbiddenError(f"ESI access forbidden: {path}")
    if status == 404:
        return ESINotFoundError(f"ESI resource not found: {path}")
    if status == 429:
        retry_after = e.response.headers.get("Retry-After")
        return ESIRateLimitError(
            "ESI rate limit exceeded",
            retry_after=int(retry_after) if retry_after else None,
        )
    if 500 <= status < 600:
        return ESIServerError(f"ESI server error: {status}", status_code=status)
    return ESIError(f"ESI request failed: {status}", status_code=status)


class ESIClient:
    """Async HTTP client for EVE Online's ESI API.

    Usage:
        async with ESIClient(user_agent, timeout) as client:
            character = await client.get_character(12345)
    """

    BASE_URL = "https://esi.evetech.net/latest"

    def __init__(self, user_agent: str, timeout: float = 30.0) -> None:
        self._user_agent = user_agent
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None
        # OrderedDict for LRU cache - most recently used items at the end
        self._etag_cache: OrderedDict[str, tuple[str, bytes]] = OrderedDict()

    def _ensure_client(self) -> httpx.AsyncClient:
        """Ensure HTTP client is initialized, raising if not.

        Returns:
            The initialized httpx.AsyncClient

        Raises:
            RuntimeError: If client not initialized via 'async with' context manager
        """
        if self._client is None:
            msg = "Client not initialized. Use 'async with' context manager."
            raise RuntimeError(msg)
        return self._client

    def _cache_etag(self, path: str, etag: str, body: bytes) -> None:
        """Cache ETag and response body with LRU eviction.

        Stores the ETag and response body for conditional GET requests.
        Evicts least-recently-used entries when cache exceeds max size.

        Args:
            path: ESI API path
            etag: ETag value from response header
            body: Response body bytes
        """
        # Remove existing entry if present (will be re-added at end)
        if path in self._etag_cache:
            del self._etag_cache[path]

        # Add to end (most recently used position)
        self._etag_cache[path] = (etag, body)

        # Evict oldest entries if over capacity
        while len(self._etag_cache) > ETAG_CACHE_MAX_SIZE:
            self._etag_cache.popitem(last=False)

    def _get_cached_etag(self, path: str) -> tuple[str, bytes] | None:
        """Get cached ETag and body, marking as recently used.

        Args:
            path: ESI API path

        Returns:
            Tuple of (etag, body) if cached, None otherwise
        """
        if path in self._etag_cache:
            # Move to end to mark as recently used
            self._etag_cache.move_to_end(path)
            return self._etag_cache[path]
        return None

    async def _retry_with_backoff(self, func: Callable[[], Awaitable[T]]) -> T:
        """Execute async function with exponential backoff retry.

        Retries on ESIServerError (5xx) and ESIRateLimitError (429) with
        exponential backoff. Respects Retry-After header when present.

        Args:
            func: Async function to execute

        Returns:
            Result of successful function call

        Raises:
            ESIError: If all retries exhausted
        """
        last_exception: ESIError | None = None

        for attempt in range(ESI_MAX_RETRIES + 1):
            try:
                return await func()
            except ESIRateLimitError as e:
                last_exception = e
                if attempt == ESI_MAX_RETRIES:
                    raise
                # Use Retry-After if provided, otherwise exponential backoff
                if e.retry_after is not None:
                    delay = float(e.retry_after)
                else:
                    delay = min(ESI_BASE_DELAY * (2**attempt) + random.uniform(0, 1), ESI_MAX_DELAY)
                await asyncio.sleep(delay)
            except ESIServerError as e:
                last_exception = e
                if attempt == ESI_MAX_RETRIES:
                    raise
                # Exponential backoff with jitter
                delay = min(ESI_BASE_DELAY * (2**attempt) + random.uniform(0, 1), ESI_MAX_DELAY)
                await asyncio.sleep(delay)

        # Unreachable - loop always returns or raises. Raise to satisfy linter/type checker.
        raise last_exception if last_exception else RuntimeError("Retry logic error")

    async def __aenter__(self) -> ESIClient:
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "User-Agent": self._user_agent,
                "X-Compatibility-Date": ESI_COMPATIBILITY_DATE,
            },
            timeout=self._timeout,
        )
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _get(self, path: str) -> bytes:
        """Perform GET request with ETag-based conditional caching and retry.

        ETag Caching Flow:
        1. Check if we have a cached ETag for this path
        2. If yes, send If-None-Match header with the cached ETag
        3. If ESI responds with 304 Not Modified, return cached body
        4. If ESI responds with 200 OK, cache the new ETag and body

        This reduces bandwidth and load on ESI for unchanged resources.
        ESI sets ETags on most endpoints and honors If-None-Match headers.

        Args:
            path: ESI API path (e.g., "/universe/systems/30000142/")

        Returns:
            Response body as bytes

        Raises:
            RuntimeError: If client not initialized
            ESIError: If request fails after retries
        """
        client = self._ensure_client()

        async def _do_request() -> bytes:
            headers: dict[str, str] = {}
            cached = self._get_cached_etag(path)
            if cached is not None:
                etag, _ = cached
                headers["If-None-Match"] = etag

            response = await client.get(path, headers=headers)

            if response.status_code == 304:
                # Content unchanged, return cached body
                _, cached_body = cached  # type: ignore[misc]
                return cached_body

            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                raise _wrap_http_error(e, path) from e

            # Cache new ETag if present
            if etag := response.headers.get("ETag"):
                self._cache_etag(path, etag, response.content)

            return response.content

        # Cast needed because ty has trouble with generic return type inference
        return cast(bytes, await self._retry_with_backoff(_do_request))

    async def _get_typed(self, path: str, response_type: type[T]) -> T:
        body = await self._get(path)
        return msgspec.json.decode(body, type=response_type)

    async def get_regions(self) -> list[int]:
        return await self._get_typed("/universe/regions/", list[int])

    async def get_region(self, region_id: int) -> Region:
        return await self._get_typed(f"/universe/regions/{region_id}/", Region)

    async def get_systems(self) -> list[int]:
        return await self._get_typed("/universe/systems/", list[int])

    async def get_system(self, system_id: int) -> System:
        return await self._get_typed(f"/universe/systems/{system_id}/", System)

    async def get_constellations(self) -> list[int]:
        return await self._get_typed("/universe/constellations/", list[int])

    async def get_constellation(self, constellation_id: int) -> Constellation:
        return await self._get_typed(f"/universe/constellations/{constellation_id}/", Constellation)

    async def get_group(self, group_id: int) -> UniverseGroup:
        return await self._get_typed(f"/universe/groups/{group_id}/", UniverseGroup)

    async def get_type(self, type_id: int) -> UniverseType:
        return await self._get_typed(f"/universe/types/{type_id}/", UniverseType)

    async def get_server_status(self) -> ServerStatus:
        """Get EVE Online server status."""
        return await self._get_typed("/status/", ServerStatus)

    async def get_character(self, character_id: int) -> ESICharacter:
        """Get public information about a character."""
        return await self._get_typed(f"/characters/{character_id}/", ESICharacter)

    async def get_corporation(self, corporation_id: int) -> ESICorporation:
        """Get public information about a corporation."""
        return await self._get_typed(f"/corporations/{corporation_id}/", ESICorporation)

    async def get_alliance(self, alliance_id: int) -> ESIAlliance:
        """Get public information about an alliance."""
        return await self._get_typed(f"/alliances/{alliance_id}/", ESIAlliance)

    async def search(
        self,
        access_token: str,
        character_id: int,
        query: str,
        categories: list[str],
    ) -> ESISearchResponse:
        """Search for entities using authenticated character search.

        Args:
            access_token: Valid EVE SSO access token
            character_id: Character ID to search as
            query: Search string (min 3 characters)
            categories: List of categories to search (character, corporation, alliance, etc.)

        Returns:
            ESISearchResponse with matching entity IDs per category
        """
        client = self._ensure_client()

        params = {
            "categories": ",".join(categories),
            "search": query,
        }
        headers = {"Authorization": f"Bearer {access_token}"}

        path = f"/characters/{character_id}/search/"
        response = await client.get(
            path,
            params=params,
            headers=headers,
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise _wrap_http_error(e, path) from e

        return msgspec.json.decode(response.content, type=ESISearchResponse)

    async def get_character_location(
        self,
        access_token: str,
        character_id: int,
    ) -> ESICharacterLocation:
        """Get character's current location.

        Args:
            access_token: Valid EVE SSO access token
            character_id: Character ID to get location for

        Returns:
            ESICharacterLocation with solar_system_id, station_id, structure_id

        Requires: esi-location.read_location.v1 scope
        """
        client = self._ensure_client()

        path = f"/characters/{character_id}/location/"
        headers = {"Authorization": f"Bearer {access_token}"}

        response = await client.get(path, headers=headers)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise _wrap_http_error(e, path) from e

        return msgspec.json.decode(response.content, type=ESICharacterLocation)

    async def get_character_online(
        self,
        access_token: str,
        character_id: int,
    ) -> ESICharacterOnline:
        """Get character's online status.

        Args:
            access_token: Valid EVE SSO access token
            character_id: Character ID to get online status for

        Returns:
            ESICharacterOnline with online status and login timestamps

        Requires: esi-location.read_online.v1 scope
        """
        client = self._ensure_client()

        path = f"/characters/{character_id}/online/"
        headers = {"Authorization": f"Bearer {access_token}"}

        response = await client.get(path, headers=headers)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise _wrap_http_error(e, path) from e

        return msgspec.json.decode(response.content, type=ESICharacterOnline)

    async def get_character_ship(
        self,
        access_token: str,
        character_id: int,
    ) -> ESICharacterShip:
        """Get character's current ship.

        Args:
            access_token: Valid EVE SSO access token
            character_id: Character ID to get ship for

        Returns:
            ESICharacterShip with ship_type_id, ship_name, ship_item_id

        Requires: esi-location.read_ship_type.v1 scope
        """
        client = self._ensure_client()

        path = f"/characters/{character_id}/ship/"
        headers = {"Authorization": f"Bearer {access_token}"}

        response = await client.get(path, headers=headers)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise _wrap_http_error(e, path) from e

        return msgspec.json.decode(response.content, type=ESICharacterShip)

    async def resolve_ids_to_names(self, ids: list[int]) -> list[ESINameResult]:
        """Resolve entity IDs to names using POST /universe/names.

        Args:
            ids: List of entity IDs to resolve (max 1000)

        Returns:
            List of ESINameResult with id, name, and category
        """
        client = self._ensure_client()

        if not ids:
            return []

        path = "/universe/names/"
        response = await client.post(
            path,
            content=msgspec.json.encode(ids),
            headers={"Content-Type": "application/json"},
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise _wrap_http_error(e, path) from e

        return msgspec.json.decode(response.content, type=list[ESINameResult])

    async def get_route(
        self,
        origin: int,
        destination: int,
        flag: str = "shortest",
    ) -> list[int]:
        """Get a route between two solar systems.

        Args:
            origin: Origin solar system ID
            destination: Destination solar system ID
            flag: Route preference - 'shortest', 'secure', or 'insecure'

        Returns:
            List of solar system IDs representing the route (includes origin and destination)
        """
        client = self._ensure_client()

        path = f"/route/{origin}/{destination}/"
        params = {"flag": flag}

        response = await client.get(path, params=params)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise _wrap_http_error(e, path) from e

        return msgspec.json.decode(response.content, type=list[int])

    async def get_structure(
        self,
        access_token: str,
        structure_id: int,
    ) -> ESIStructure:
        """Get structure information.

        Args:
            access_token: Valid EVE SSO access token
            structure_id: Structure ID to get info for

        Returns:
            ESIStructure with name, owner_id, solar_system_id, etc.

        Requires: esi-universe.read_structures.v1 scope
        Raises: ESIForbiddenError if user not on structure ACL
        """
        client = self._ensure_client()

        path = f"/universe/structures/{structure_id}/"
        headers = {"Authorization": f"Bearer {access_token}"}

        response = await client.get(path, headers=headers)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise _wrap_http_error(e, path) from e

        return msgspec.json.decode(response.content, type=ESIStructure)


async def provide_esi_client(app_settings: Settings) -> ESIClient:
    """Provide ESIClient for dependency injection.

    Args:
        app_settings: Application settings

    Returns:
        Configured ESIClient instance
    """
    return ESIClient(app_settings.esi.user_agent, app_settings.esi.timeout)
