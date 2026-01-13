from __future__ import annotations

from litestar.config.cors import CORSConfig

from config import get_settings

settings = get_settings()

cors_config = CORSConfig(
    allow_origins=settings.cors.allow_origins,
    allow_methods=settings.cors.allow_methods,  # type: ignore
    allow_headers=settings.cors.allow_headers,
    allow_credentials=settings.cors.allow_credentials,
)
