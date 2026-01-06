from __future__ import annotations

from litestar import Litestar
from litestar.di import Provide

from api.di import channels_plugin, provide_valkey_client, rl_store, sessions_store, sqlspec_plugin
from api.middleware import (
    auth_middleware,
    compression_config,
    cors_config,
    csrf_config,
    session_config,
)
from config import get_settings
from routes import AuthController, HealthController, MapController, UniverseController, UserController


def create_app() -> Litestar:
    settings = get_settings()

    return Litestar(
        route_handlers=[AuthController, HealthController, MapController, UniverseController, UserController],
        plugins=[sqlspec_plugin, channels_plugin],
        stores={
            "sessions": sessions_store,
            "rate_limit": rl_store,
        },
        dependencies={"valkey_client": Provide(provide_valkey_client)},
        middleware=[session_config.middleware, auth_middleware],
        cors_config=cors_config,
        csrf_config=csrf_config,
        compression_config=compression_config,
        debug=settings.debug,
    )


app = create_app()
