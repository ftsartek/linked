from litestar import Litestar
from litestar.config.compression import CompressionConfig
from litestar.config.cors import CORSConfig
from litestar.config.csrf import CSRFConfig

from config import get_settings


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

    return Litestar(
        route_handlers=[],
        cors_config=cors_config,
        csrf_config=csrf_config,
        compression_config=compression_config,
        debug=settings.debug,
    )


app = create_app()