"""ASGI application entrypoint.

This module creates the singleton Litestar application instance.
Point your ASGI server here: api.main:app
"""

from __future__ import annotations

from litestar.di import Provide

from config import Settings, get_settings
from esi_client import provide_esi_client
from services.eve_sso import provide_sso_service

from .app import create_app
from .di import get_channels_plugin, get_rl_store, get_sessions_store, provide_valkey_client, sqlspec_plugin
from .middleware import auth_middleware, cors_config, csrf_config, session_config


def provide_settings() -> Settings:
    """Provide application settings for dependency injection."""
    return get_settings()


app = create_app(
    plugins=[sqlspec_plugin, get_channels_plugin()],
    middleware=[session_config.middleware, auth_middleware],
    cors=cors_config,
    csrf=csrf_config,
    stores={
        "sessions": get_sessions_store(),
        "rate_limit": get_rl_store(),
    },
    dependencies={
        "settings": Provide(provide_settings),
        "valkey_client": Provide(provide_valkey_client),
        "sso_service": Provide(provide_sso_service),
        "esi_client": Provide(provide_esi_client),
    },
)
