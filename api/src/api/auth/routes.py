from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Any

from litestar import Controller, Response, get, post
from litestar.exceptions import NotAuthorizedException, NotFoundException
from litestar.response import Redirect

from api.auth.guards import require_auth
from api.auth.middleware import SessionUser
from config import get_settings
from database import provide_session
from database.models.character import Character, INSERT_STMT as CHARACTER_INSERT
from database.models.refresh_token import (
    UPSERT_STMT as REFRESH_TOKEN_UPSERT,
    SELECT_BY_CHARACTER_STMT as REFRESH_TOKEN_SELECT,
)
from database.models.user import User, INSERT_STMT as USER_INSERT
from services.encryption import get_encryption_service
from services.eve_sso import get_sso_service


@dataclass
class UserInfo:
    """Current user information."""

    id: int
    characters: list[CharacterInfo]


@dataclass
class CharacterInfo:
    """Character information for API responses."""

    id: int
    name: str
    corporation_id: int | None
    alliance_id: int | None


class AuthController(Controller):
    """Authentication endpoints for EVE SSO."""

    path = "/auth"

    @get("/login")
    async def login(self, request: Any) -> Redirect:
        """Initiate EVE SSO login flow.

        Generates a random state parameter, stores it in session,
        and redirects to EVE SSO authorization page.
        """
        state = secrets.token_urlsafe(32)
        request.session["oauth_state"] = state
        request.session["linking"] = False

        sso = get_sso_service()
        auth_url = sso.get_authorization_url(state)

        return Redirect(path=auth_url)

    @get("/link", guards=[require_auth])
    async def link(self, request: Any) -> Redirect:
        """Initiate EVE SSO flow to link additional character.

        Requires authenticated user. Redirects to EVE SSO to authorize
        a new character that will be linked to the current account.
        """
        state = secrets.token_urlsafe(32)
        request.session["oauth_state"] = state
        request.session["linking"] = True

        sso = get_sso_service()
        auth_url = sso.get_authorization_url(state)

        return Redirect(path=auth_url)

    @get("/callback")
    async def callback(self, request: Any, code: str, oauth_state: str) -> Redirect:
        """Handle EVE SSO callback.

        Validates state, exchanges code for tokens, and either:
        - Creates new user if character is unknown and not linking
        - Logs in existing user if character is known
        - Links character to current user if linking mode

        Args:
            code: Authorization code from EVE SSO
            oauth_state: State parameter for CSRF validation (named to avoid Litestar reserved 'state')

        Returns:
            Redirect to frontend
        """
        settings = get_settings()

        # Validate state parameter
        expected_state = request.session.get("oauth_state")
        if not expected_state or oauth_state != expected_state:
            raise NotAuthorizedException("Invalid state parameter")

        # Clear state from session
        del request.session["oauth_state"]
        is_linking = request.session.pop("linking", False)

        # Exchange code for tokens
        sso = get_sso_service()
        tokens = await sso.exchange_code(code)

        # Validate JWT and extract character info
        char_info = sso.validate_jwt(tokens.access_token)

        async with provide_session() as session:
            # Check if character already exists
            result = await session.execute(
                "SELECT id, user_id, name, corporation_id, alliance_id FROM character WHERE id = $1",
                char_info.character_id,
            )
            existing_char = await result.fetchone()

            if is_linking:
                # Linking mode: must be logged in
                current_user: SessionUser | None = request.user
                if current_user is None:
                    raise NotAuthorizedException("Must be logged in to link characters")

                if existing_char is not None:
                    existing_user_id = existing_char[1]
                    if existing_user_id != current_user.id:
                        raise NotAuthorizedException(
                            "Character is already linked to another account"
                        )
                    # Character already linked to this user, just update tokens
                else:
                    # Create new character linked to current user
                    await session.execute(
                        CHARACTER_INSERT,
                        char_info.character_id,
                        current_user.id,
                        char_info.character_name,
                        None,  # corporation_id - will be fetched from ESI later
                        None,  # alliance_id
                    )

                user_id = current_user.id
            else:
                # Normal login mode
                if existing_char is not None:
                    # Character exists, log in as that user
                    user_id = existing_char[1]
                else:
                    # Create new user and character
                    result = await session.execute(USER_INSERT)
                    new_user = await result.fetchone()
                    user_id = new_user[0]

                    await session.execute(
                        CHARACTER_INSERT,
                        char_info.character_id,
                        user_id,
                        char_info.character_name,
                        None,
                        None,
                    )

            # Store encrypted refresh token
            encryption = get_encryption_service()
            encrypted_token = encryption.encrypt(tokens.refresh_token)

            await session.execute(
                REFRESH_TOKEN_UPSERT,
                char_info.character_id,
                encrypted_token,
                char_info.scopes,
                None,  # expires_at - refresh tokens don't have explicit expiry
            )

        # Set session data
        request.session["user_id"] = user_id
        request.session["character_id"] = char_info.character_id
        request.session["character_name"] = char_info.character_name

        return Redirect(path=settings.frontend_url)

    @post("/logout")
    async def logout(self, request: Any) -> dict[str, bool]:
        """Log out current user by clearing session."""
        request.session.clear()
        return {"success": True}

    @get("/me", guards=[require_auth])
    async def me(self, request: Any) -> UserInfo:
        """Get current authenticated user and their linked characters."""
        user: SessionUser = request.user

        async with provide_session() as session:
            result = await session.execute(
                """
                SELECT id, name, corporation_id, alliance_id
                FROM character
                WHERE user_id = $1
                ORDER BY name
                """,
                user.id,
            )
            rows = await result.fetchall()

        characters = [
            CharacterInfo(
                id=row[0],
                name=row[1],
                corporation_id=row[2],
                alliance_id=row[3],
            )
            for row in rows
        ]

        return UserInfo(id=user.id, characters=characters)
