from __future__ import annotations

from typing import TypeVar

import httpx
import msgspec

from config import Settings

from .exceptions import ESIError, ESINotFoundError, ESIRateLimitError, ESIServerError
from .models import (
    Constellation,
    ESIAlliance,
    ESICharacter,
    ESICorporation,
    ESINameResult,
    ESISearchResponse,
    Region,
    System,
    UniverseGroup,
    UniverseType,
)

T = TypeVar("T")


def _wrap_http_error(e: httpx.HTTPStatusError, path: str) -> ESIError:
    """Wrap an httpx.HTTPStatusError in a domain-specific ESI exception."""
    status = e.response.status_code
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
    BASE_URL = "https://esi.evetech.net/latest"

    def __init__(self, user_agent: str, timeout: float = 30.0) -> None:
        self._user_agent = user_agent
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None
        self._etag_cache: dict[str, tuple[str, bytes]] = {}

    async def __aenter__(self) -> ESIClient:
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={"User-Agent": self._user_agent},
            timeout=self._timeout,
        )
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _get(self, path: str) -> bytes:
        if self._client is None:
            msg = "Client not initialized. Use 'async with' context manager."
            raise RuntimeError(msg)

        headers: dict[str, str] = {}
        if path in self._etag_cache:
            etag, _ = self._etag_cache[path]
            headers["If-None-Match"] = etag

        response = await self._client.get(path, headers=headers)

        if response.status_code == 304:
            _, cached_body = self._etag_cache[path]
            return cached_body

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise _wrap_http_error(e, path) from e

        if etag := response.headers.get("ETag"):
            self._etag_cache[path] = (etag, response.content)

        return response.content

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
        if self._client is None:
            msg = "Client not initialized. Use 'async with' context manager."
            raise RuntimeError(msg)

        params = {
            "categories": ",".join(categories),
            "search": query,
        }
        headers = {"Authorization": f"Bearer {access_token}"}

        path = f"/characters/{character_id}/search/"
        response = await self._client.get(
            path,
            params=params,
            headers=headers,
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise _wrap_http_error(e, path) from e

        return msgspec.json.decode(response.content, type=ESISearchResponse)

    async def resolve_ids_to_names(self, ids: list[int]) -> list[ESINameResult]:
        """Resolve entity IDs to names using POST /universe/names.

        Args:
            ids: List of entity IDs to resolve (max 1000)

        Returns:
            List of ESINameResult with id, name, and category
        """
        if self._client is None:
            msg = "Client not initialized. Use 'async with' context manager."
            raise RuntimeError(msg)

        if not ids:
            return []

        path = "/universe/names/"
        response = await self._client.post(
            path,
            content=msgspec.json.encode(ids),
            headers={"Content-Type": "application/json"},
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise _wrap_http_error(e, path) from e

        return msgspec.json.decode(response.content, type=list[ESINameResult])


async def provide_esi_client(app_settings: Settings) -> ESIClient:
    """Provide ESIClient for dependency injection.

    Args:
        app_settings: Application settings

    Returns:
        Configured ESIClient instance
    """
    return ESIClient(app_settings.esi.user_agent, app_settings.esi.timeout)
