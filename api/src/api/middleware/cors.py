from __future__ import annotations

from litestar.config.cors import CORSConfig

from config import get_settings

settings = get_settings()

cors_config = CORSConfig(
    allow_origins=settings.cors_allow_origins,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
    allow_credentials=settings.cors_allow_credentials,
)
