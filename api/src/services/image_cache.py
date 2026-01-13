from __future__ import annotations

import asyncio
import time
from pathlib import Path

import httpx

from config import get_settings

# EVE image URL patterns
EVE_IMAGE_BASE = "https://images.evetech.net"
ENTITY_IMAGE_PATHS = {
    "character": "/characters/{id}/portrait",
    "corporation": "/corporations/{id}/logo",
    "alliance": "/alliances/{id}/logo",
}
VALID_SIZES = {32, 64, 128, 256, 512, 1024}
DEFAULT_SIZE = 64


class ImageCacheService:
    """Service for caching EVE entity images on disk."""

    def __init__(self) -> None:
        settings = get_settings()
        self.cache_dir = Path(settings.image_cache.dir)
        self.ttl_seconds = settings.image_cache.ttl_seconds
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, entity_type: str, entity_id: int, size: int) -> Path:
        """Generate cache file path for an image."""
        filename = f"{entity_type}_{entity_id}_{size}.png"
        return self.cache_dir / filename

    def _is_cache_valid(self, cache_path: Path) -> bool:
        """Check if cached file exists and is not expired."""
        if not cache_path.exists():
            return False
        age = time.time() - cache_path.stat().st_mtime
        return age < self.ttl_seconds

    async def get_image(
        self,
        entity_type: str,
        entity_id: int,
        size: int = DEFAULT_SIZE,
    ) -> tuple[bytes, str] | None:
        """Get image from cache or fetch from EVE API.

        Returns:
            Tuple of (image_bytes, content_type) or None if fetch failed.
        """
        if size not in VALID_SIZES:
            size = DEFAULT_SIZE

        cache_path = self._get_cache_path(entity_type, entity_id, size)

        # Return cached image if valid
        if self._is_cache_valid(cache_path):
            return await asyncio.to_thread(cache_path.read_bytes), "image/png"

        # Fetch from EVE API
        path_template = ENTITY_IMAGE_PATHS.get(entity_type)
        if path_template is None:
            return None

        url = f"{EVE_IMAGE_BASE}{path_template.format(id=entity_id)}?size={size}"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    image_data = response.content
                    content_type = response.headers.get("content-type", "image/png")

                    # Cache the image asynchronously
                    await asyncio.to_thread(cache_path.write_bytes, image_data)

                    return image_data, content_type

        except httpx.RequestError:
            # If fetch fails but we have stale cache, return it
            if cache_path.exists():
                return await asyncio.to_thread(cache_path.read_bytes), "image/png"

        return None


async def provide_image_cache_service() -> ImageCacheService:
    """Provide image cache service for dependency injection."""
    return ImageCacheService()
