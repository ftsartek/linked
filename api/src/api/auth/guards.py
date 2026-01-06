from __future__ import annotations

from litestar.connection import ASGIConnection
from litestar.exceptions import NotAuthorizedException
from litestar.handlers import BaseRouteHandler


def require_auth(connection: ASGIConnection, _: BaseRouteHandler) -> None:
    """Guard that requires an authenticated user.

    Raises:
        NotAuthorizedException: If user is not authenticated
    """
    if connection.user is None:
        raise NotAuthorizedException("Authentication required")
