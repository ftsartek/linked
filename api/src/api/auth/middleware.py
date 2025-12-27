from __future__ import annotations

from dataclasses import dataclass

from litestar.connection import ASGIConnection
from litestar.middleware import AbstractAuthenticationMiddleware, AuthenticationResult

from database.models.user import User


@dataclass
class SessionUser:
    """User data stored in session and available via request.user."""

    id: int
    character_id: int
    character_name: str


class AuthenticationMiddleware(AbstractAuthenticationMiddleware):
    """Middleware that loads user from session.

    Sets request.user to SessionUser if authenticated, None otherwise.
    Does not raise exceptions - let guards handle authorization.
    """

    async def authenticate_request(self, connection: ASGIConnection) -> AuthenticationResult:
        """Extract user from session.

        Args:
            connection: The ASGI connection

        Returns:
            AuthenticationResult with user data or None
        """
        session = connection.session

        # Check if session has user data
        user_id = session.get("user_id")
        if user_id is None:
            return AuthenticationResult(user=None, auth=None)

        character_id = session.get("character_id")
        character_name = session.get("character_name", "")

        user = SessionUser(
            id=user_id,
            character_id=character_id,
            character_name=character_name,
        )

        return AuthenticationResult(user=user, auth=None)
