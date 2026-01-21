from __future__ import annotations

from typing import Any

from litestar.connection import ASGIConnection
from litestar.exceptions import NotAuthorizedException, PermissionDeniedException
from litestar.handlers import BaseRouteHandler

from api.di.sqlspec import provide_session_from_scope
from services.instance_acl import InstanceACLService


def require_auth(connection: ASGIConnection, _: BaseRouteHandler) -> None:
    """Guard that requires an authenticated user.

    Raises:
        NotAuthorizedException: If user is not authenticated (401)
    """
    if connection.user is None:
        raise NotAuthorizedException("Authentication required")


async def require_acl_access(connection: ASGIConnection[Any, Any, Any, Any], _: BaseRouteHandler) -> None:
    """Guard that requires user to pass instance ACL.

    User must be authenticated AND either:
    - Be the instance owner
    - Be an instance admin
    - Pass the ACL check (character/corporation/alliance match)
    - Instance is open

    Raises:
        NotAuthorizedException: If user is not authenticated (401)
        PermissionDeniedException: If user doesn't pass ACL (403)
    """
    if connection.user is None:
        raise NotAuthorizedException("Authentication required")

    async with provide_session_from_scope(connection.app.state, connection.scope) as db_session:
        acl_service = InstanceACLService(db_session)
        has_access = await acl_service.check_user_access(connection.user.id)
        if not has_access:
            raise PermissionDeniedException("Access denied by instance ACL")


async def require_admin(connection: ASGIConnection[Any, Any, Any, Any], _: BaseRouteHandler) -> None:
    """Guard that requires user to be owner OR admin.

    Raises:
        NotAuthorizedException: If user is not authenticated (401)
        PermissionDeniedException: If user is not privileged (403)
    """
    if connection.user is None:
        raise NotAuthorizedException("Authentication required")

    async with provide_session_from_scope(connection.app.state, connection.scope) as db_session:
        acl_service = InstanceACLService(db_session)
        is_privileged = await acl_service.is_privileged(connection.user.id)
        if not is_privileged:
            raise PermissionDeniedException("Admin access required")


async def require_owner(connection: ASGIConnection[Any, Any, Any, Any], _: BaseRouteHandler) -> None:
    """Guard that requires user to be the instance owner.

    Raises:
        NotAuthorizedException: If user is not authenticated (401)
        PermissionDeniedException: If user is not the owner (403)
    """
    if connection.user is None:
        raise NotAuthorizedException("Authentication required")

    async with provide_session_from_scope(connection.app.state, connection.scope) as db_session:
        acl_service = InstanceACLService(db_session)
        is_owner = await acl_service.is_owner(connection.user.id)
        if not is_owner:
            raise PermissionDeniedException("Owner access required")
