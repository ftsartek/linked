from __future__ import annotations

from litestar.config.compression import CompressionConfig

from config import get_settings

settings = get_settings()

compression_config = CompressionConfig(
    backend="brotli",
    minimum_size=settings.compression_minimum_size,
    brotli_quality=settings.compression_brotli_quality,
    brotli_gzip_fallback=True,
)
