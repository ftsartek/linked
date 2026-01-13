"""Litestar application factory.

This module provides the create_app() factory function.
For the application instance, see api.main:app
"""

from __future__ import annotations

from collections.abc import Sequence

from litestar import Litestar
from litestar.config.cors import CORSConfig
from litestar.config.csrf import CSRFConfig
from litestar.di import Provide
from litestar.plugins import PluginProtocol
from litestar.stores.base import Store
from litestar.stores.registry import StoreRegistry
from litestar.types import ControllerRouterHandler, Middleware

from config import get_settings
from routes import AuthController, HealthController, MapController, UniverseController, UserController

from .handlers import exception_handlers
from .middleware import compression_config

DEFAULT_ROUTE_HANDLERS: list[ControllerRouterHandler] = [
    AuthController,
    HealthController,
    MapController,
    UniverseController,
    UserController,
]


def create_app(
    *,
    plugins: list[PluginProtocol] = [],
    dependencies: dict[str, Provide] = {},
    stores: StoreRegistry | dict[str, Store] = {},
    middleware: Sequence[Middleware] = [],
    cors: CORSConfig | None = None,
    csrf: CSRFConfig | None = None,
    extra_route_handlers: list[ControllerRouterHandler] | None = None,
) -> Litestar:
    """Create a Litestar application instance.

    Args:
        plugins: List of Litestar plugins (SQLSpec, Channels, etc.)
        dependencies: Dependency injection providers
        stores: Store registry for sessions, rate limiting, etc.
        middleware: Middleware stack
        cors: CORS configuration
        csrf: CSRF configuration (None to disable)
        extra_route_handlers: Additional route handlers to include

    Returns:
        Configured Litestar application
    """
    settings = get_settings()

    route_handlers = [*DEFAULT_ROUTE_HANDLERS]
    if extra_route_handlers:
        route_handlers.extend(extra_route_handlers)

    return Litestar(
        route_handlers=route_handlers,
        plugins=plugins,
        stores=stores,
        exception_handlers=exception_handlers,  # ty: ignore
        dependencies=dependencies,
        middleware=middleware,
        cors_config=cors,
        csrf_config=csrf,
        compression_config=compression_config,
        debug=settings.debug,
    )
