from __future__ import annotations

from litestar.middleware import DefineMiddleware

from api.auth import AuthenticationMiddleware
from config import get_settings

settings = get_settings()

auth_middleware = DefineMiddleware(
    AuthenticationMiddleware,
    exclude=["^/schema", "^/health"],
)
