from __future__ import annotations

from litestar.middleware.session.server_side import ServerSideSessionConfig

from config import get_settings

settings = get_settings()

# Session configuration with Valkey backend
session_config = ServerSideSessionConfig(
    key="session",
    max_age=settings.session.max_age,
    renew_on_access=True,
)
