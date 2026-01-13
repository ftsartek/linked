from __future__ import annotations

from litestar.di import Provide

from api.app import create_app
from api.di import (
    get_channels_plugin,
    get_rl_store,
    get_sessions_store,
    provide_settings,
    provide_valkey_client,
    sqlspec_plugin,
)
from api.middleware import auth_middleware, session_config
from tests.fixtures.mock_esi_client import provide_mock_esi_client
from tests.fixtures.mock_sso import provide_mock_sso_service

from .routes import test_router

app = create_app(
    plugins=[sqlspec_plugin, get_channels_plugin()],
    middleware=[session_config.middleware, auth_middleware],
    cors=None,
    csrf=None,  # Disabled for testing
    stores={
        "sessions": get_sessions_store(),
        "rate_limit": get_rl_store(),
    },
    dependencies={
        "settings": Provide(provide_settings),
        "valkey_client": Provide(provide_valkey_client),
        "sso_service": Provide(provide_mock_sso_service),
        "esi_client": Provide(provide_mock_esi_client),
    },
    extra_route_handlers=[test_router],
)
