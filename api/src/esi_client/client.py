from typing import TypeVar

import httpx
import msgspec

from .models import Constellation, Region, System

T = TypeVar("T")


class ESIClient:
    BASE_URL = "https://esi.evetech.net/latest"

    def __init__(self, user_agent: str, timeout: float = 30.0) -> None:
        self._user_agent = user_agent
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None
        self._etag_cache: dict[str, tuple[str, bytes]] = {}

    async def __aenter__(self) -> "ESIClient":
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

        response.raise_for_status()

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
        return await self._get_typed(
            f"/universe/constellations/{constellation_id}/", Constellation
        )
