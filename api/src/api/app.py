from litestar import Litestar
from litestar.config.compression import CompressionConfig
from litestar.config.cors import CORSConfig
from litestar.config.csrf import CSRFConfig
from litestar.middleware import DefineMiddleware
from litestar.middleware.session.server_side import ServerSideSessionConfig
from litestar.stores.valkey import ValkeyStore
from sqlspec.extensions.litestar import SQLSpecPlugin

from api.auth import AuthenticationMiddleware
from config import get_settings
from database import sql
from routes import AuthController


def create_app() -> Litestar:
    settings = get_settings()


    cors_config = CORSConfig(
        allow_origins=settings.cors_allow_origins,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
        allow_credentials=settings.cors_allow_credentials,
    )

    csrf_config = CSRFConfig(secret=settings.csrf_secret)

    compression_config = CompressionConfig(
        backend="brotli",
        minimum_size=settings.compression_minimum_size,
        brotli_quality=settings.compression_brotli_quality,
        brotli_gzip_fallback=True,
    )

    # Session configuration with Valkey backend
    session_config = ServerSideSessionConfig(
        key="session",
        max_age=settings.session_max_age,
    )

    # Authentication middleware (runs after session middleware)
    auth_middleware = DefineMiddleware(
        AuthenticationMiddleware,
        exclude=["^/schema", "^/health"],
    )

    sqlspec_plugin = SQLSpecPlugin(sqlspec=sql)

    return Litestar(
        route_handlers=[AuthController],
        plugins=[sqlspec_plugin],
        stores={"sessions": ValkeyStore.with_client(url=settings.valkey_url)},
        middleware=[session_config.middleware, auth_middleware],
        cors_config=cors_config,
        csrf_config=csrf_config,
        compression_config=compression_config,
        debug=settings.debug,
    )


app = create_app()