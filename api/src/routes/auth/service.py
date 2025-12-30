from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlspec import AsyncDriverAdapterBase

from api.auth.middleware import SessionUser
from database.models.character import INSERT_STMT as CHARACTER_INSERT
from database.models.refresh_token import UPSERT_STMT as REFRESH_TOKEN_UPSERT
from database.models.user import INSERT_STMT as USER_INSERT
from services.encryption import EncryptionService
from services.eve_sso import CharacterInfo as SSOCharacterInfo
from services.eve_sso import EveSSOService, TokenResponse


@dataclass
class CharacterInfo:
    """Character information for API responses."""

    id: int
    name: str
    corporation_id: int | None
    alliance_id: int | None


@dataclass
class CharacterUserInfo:
    id: int
    user_id: UUID
    name: str
    corporation_id: int | None
    alliance_id: int | None


@dataclass
class UserInfo:
    """Current user information."""

    id: UUID
    characters: list[CharacterInfo]


@dataclass
class CallbackResult:
    """Result of SSO callback processing."""

    user_id: UUID
    character_id: int
    character_name: str


class AuthService:
    """Authentication business logic."""

    def __init__(
        self,
        db_session: AsyncDriverAdapterBase,
        sso_service: EveSSOService,
        encryption_service: EncryptionService,
    ) -> None:
        self.db_session = db_session
        self.sso_service = sso_service
        self.encryption_service = encryption_service

    async def get_character_by_id(self, character_id: int) -> CharacterUserInfo | None:
        """Fetch character by EVE character ID.

        Returns:
            Tuple of (id, user_id, name, corporation_id, alliance_id) or None
        """
        return await self.db_session.select_one_or_none(
            "SELECT id, user_id, name, corporation_id, alliance_id FROM character WHERE id = $1",
            character_id,
            schema_type=CharacterUserInfo,
        )

    async def create_user(self) -> UUID:
        """Create a new user.

        Returns:
            The new user's ID
        """
        return await self.db_session.select_value(USER_INSERT)

    async def create_character(
        self,
        character_id: int,
        user_id: UUID,
        name: str,
        corporation_id: int | None = None,
        alliance_id: int | None = None,
    ) -> None:
        """Create character linked to user."""
        await self.db_session.execute(
            CHARACTER_INSERT,
            character_id,
            user_id,
            name,
            corporation_id,
            alliance_id,
        )

    async def store_refresh_token(
        self,
        character_id: int,
        refresh_token: str,
        scopes: list[str],
    ) -> None:
        """Store encrypted refresh token."""
        token = self.encryption_service.encrypt(refresh_token)

        await self.db_session.execute(
            REFRESH_TOKEN_UPSERT,
            character_id,
            token,
            scopes,
            None,  # expires_at - refresh tokens don't have explicit expiry
        )

    async def get_user_characters(self, user_id: UUID) -> list[CharacterInfo]:
        """Get all characters for a user."""
        return await self.db_session.select(
            """
            SELECT id, name, corporation_id, alliance_id
            FROM character
            WHERE user_id = $1
            ORDER BY name
            """,
            user_id,
            schema_type=CharacterInfo,
        )

    async def get_current_user(self, session_user: SessionUser) -> UserInfo:
        """Get current user with all linked characters."""
        characters = await self.get_user_characters(session_user.id)
        return UserInfo(id=session_user.id, characters=characters)

    async def process_callback(
        self,
        code: str,
        current_user: SessionUser | None,
        is_linking: bool,
    ) -> CallbackResult:
        """Process SSO callback - exchange code, validate, and create/link user.

        Args:
            code: Authorization code from EVE SSO
            current_user: Current session user (if authenticated)
            is_linking: Whether this is a character linking operation

        Returns:
            CallbackResult with user and character info for session

        Raises:
            ValueError: If linking but not logged in, or character belongs to another user
        """
        # Exchange code for tokens
        tokens = await self.sso_service.exchange_code(code)

        # Validate JWT and extract character info
        char_info = self.sso_service.validate_jwt(tokens.access_token)

        # Process the callback (create/link user, store tokens)
        user_id = await self._handle_sso_callback(
            char_info=char_info,
            tokens=tokens,
            current_user=current_user,
            is_linking=is_linking,
        )

        return CallbackResult(
            user_id=user_id,
            character_id=char_info.character_id,
            character_name=char_info.character_name,
        )

    async def _handle_sso_callback(
        self,
        char_info: SSOCharacterInfo,
        tokens: TokenResponse,
        current_user: SessionUser | None,
        is_linking: bool,
    ) -> UUID:
        """Internal: Process SSO callback - create/link user and store tokens.

        Args:
            char_info: Character info from JWT validation
            tokens: Token response from SSO
            current_user: Current session user (if authenticated)
            is_linking: Whether this is a character linking operation

        Returns:
            The user ID to set in session

        Raises:
            ValueError: If linking but not logged in, or character belongs to another user
        """
        existing_char = await self.get_character_by_id(char_info.character_id)

        if is_linking:
            if current_user is None:
                raise ValueError("Must be logged in to link characters")

            if existing_char is not None:
                if existing_char.user_id != current_user.id:
                    raise ValueError("Character is already linked to another account")
                # Character already linked to this user, just update tokens
            else:
                # Create new character linked to current user
                await self.create_character(
                    char_info.character_id,
                    current_user.id,
                    char_info.character_name,
                )

            user_id = current_user.id
        else:
            # Normal login mode
            if existing_char is not None:
                # Character exists, log in as that user
                user_id = existing_char.user_id
            else:
                # Create new user and character
                user_id = await self.create_user()
                await self.create_character(
                    char_info.character_id,
                    user_id,
                    char_info.character_name,
                )

        # Store encrypted refresh token
        await self.store_refresh_token(
            char_info.character_id,
            tokens.refresh_token,
            char_info.scopes,
        )

        return user_id


async def provide_auth_service(
    db_session: AsyncDriverAdapterBase,
    sso_service: EveSSOService,
    encryption_service: EncryptionService,
) -> AuthService:
    """Provide AuthService with injected dependencies."""
    return AuthService(db_session, sso_service, encryption_service)
