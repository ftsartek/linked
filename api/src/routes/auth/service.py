from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlspec import AsyncDriverAdapterBase
from valkey.asyncio import Valkey

from api.auth.middleware import SessionUser
from database.models.alliance import INSERT_STMT as ALLIANCE_INSERT
from database.models.character import INSERT_STMT as CHARACTER_INSERT
from database.models.corporation import INSERT_STMT as CORPORATION_INSERT
from database.models.map_subscription import INSERT_STMT as MAP_SUBSCRIPTION_INSERT
from database.models.refresh_token import UPSERT_STMT as REFRESH_TOKEN_UPSERT
from database.models.user import INSERT_STMT as USER_INSERT
from esi_client import ESIClient
from services.encryption import EncryptionService
from services.eve_sso import CharacterInfo as SSOCharacterInfo
from services.eve_sso import EveSSOService, ScopeGroup, TokenResponse, has_scope_group
from services.instance_acl import InstanceACLService

logger = logging.getLogger(__name__)


class ACLDeniedError(Exception):
    """Raised when access is denied by instance ACL."""

    pass


@dataclass
class CharacterInfo:
    """Character information for API responses."""

    id: int
    name: str
    corporation_id: int | None
    alliance_id: int | None
    date_created: datetime
    scope_groups: list[str]


@dataclass
class CharacterWithScopes:
    """Raw character data with scope flags from database."""

    id: int
    name: str
    corporation_id: int | None
    alliance_id: int | None
    date_created: datetime
    has_location_scope: bool
    has_search_scope: bool


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
    primary_character_id: int | None
    characters: list[CharacterInfo]
    is_owner: bool = False
    is_admin: bool = False
    can_create_maps: bool = True


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
        esi_client: ESIClient,
        acl_service: InstanceACLService,
        location_cache: Valkey | None = None,
    ) -> None:
        self.db_session = db_session
        self.sso_service = sso_service
        self.encryption_service = encryption_service
        self.esi_client = esi_client
        self.acl_service = acl_service
        self.location_cache = location_cache

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

    async def set_primary_character(self, user_id: UUID, character_id: int) -> None:
        """Set the primary character for a user."""
        await self.db_session.execute(
            'UPDATE "user" SET primary_character_id = $2, date_updated = NOW() WHERE id = $1',
            user_id,
            character_id,
        )

    async def store_refresh_token(
        self,
        character_id: int,
        refresh_token: str,
        scopes: list[str],
        has_location_scope: bool = False,
        has_search_scope: bool = False,
    ) -> None:
        """Store encrypted refresh token with scope group flags.

        Args:
            character_id: EVE character ID
            refresh_token: The refresh token to encrypt and store
            scopes: List of granted scopes
            has_location_scope: Whether location scopes were granted
            has_search_scope: Whether search scopes were granted
        """
        token = self.encryption_service.encrypt(refresh_token)

        await self.db_session.execute(
            REFRESH_TOKEN_UPSERT,
            character_id,
            token,
            scopes,
            None,  # expires_at - refresh tokens don't have explicit expiry
            has_location_scope,
            has_search_scope,
        )

    async def _clear_location_cache(self, character_id: int) -> None:
        """Clear location cache entries when scope is removed.

        Called when a character re-authorizes without location scope
        but previously had it. This ensures stale location data is removed.

        Note: We can't emit CHARACTER_LEFT events here because we don't
        have the full user context. The character will disappear from
        nodes on next map load.
        """
        if self.location_cache is None:
            return

        await self.location_cache.delete(f"{character_id}:position")
        await self.location_cache.delete(f"{character_id}:online")
        await self.location_cache.delete(f"{character_id}:ship")
        await self.location_cache.delete(f"char_prev_loc:{character_id}")

    async def upsert_corporation(
        self,
        corporation_id: int,
        name: str,
        ticker: str,
        alliance_id: int | None = None,
        member_count: int | None = None,
    ) -> None:
        """Upsert a corporation into the database."""
        await self.db_session.execute(
            CORPORATION_INSERT,
            corporation_id,
            name,
            ticker,
            alliance_id,
            member_count,
        )

    async def upsert_alliance(
        self,
        alliance_id: int,
        name: str,
        ticker: str,
    ) -> None:
        """Upsert an alliance into the database."""
        await self.db_session.execute(
            ALLIANCE_INSERT,
            alliance_id,
            name,
            ticker,
        )

    async def fetch_and_upsert_affiliations(
        self,
        character_id: int,
    ) -> tuple[int | None, int | None]:
        """Fetch character's corporation and alliance from ESI and upsert them.

        Returns:
            Tuple of (corporation_id, alliance_id)
        """
        corporation_id: int | None = None
        alliance_id: int | None = None

        try:
            async with self.esi_client as client:
                # Fetch character public info
                char_info = await client.get_character(character_id)
                corporation_id = char_info.corporation_id
                alliance_id = char_info.alliance_id

                # Fetch and upsert corporation
                if corporation_id:
                    corp_info = await client.get_corporation(corporation_id)
                    await self.upsert_corporation(
                        corporation_id=corporation_id,
                        name=corp_info.name,
                        ticker=corp_info.ticker,
                        alliance_id=corp_info.alliance_id,
                        member_count=corp_info.member_count,
                    )

                # Fetch and upsert alliance
                if alliance_id:
                    ally_info = await client.get_alliance(alliance_id)
                    await self.upsert_alliance(
                        alliance_id=alliance_id,
                        name=ally_info.name,
                        ticker=ally_info.ticker,
                    )

        except Exception:
            # Log but don't fail the login if ESI is unavailable
            logger.exception("Failed to fetch character affiliations from ESI")

        return corporation_id, alliance_id

    async def get_user_characters(self, user_id: UUID) -> list[CharacterInfo]:
        """Get all characters for a user with their scope groups."""
        rows = await self.db_session.select(
            """
            SELECT
                c.id,
                c.name,
                c.corporation_id,
                c.alliance_id,
                c.date_created,
                COALESCE(rt.has_location_scope, FALSE) as has_location_scope,
                COALESCE(rt.has_search_scope, FALSE) as has_search_scope
            FROM character c
            LEFT JOIN refresh_token rt ON rt.character_id = c.id
            WHERE c.user_id = $1
            ORDER BY c.name
            """,
            user_id,
            schema_type=CharacterWithScopes,
        )

        # Map boolean scope flags to list of scope group strings
        result = []
        for row in rows:
            scope_groups = []
            if row.has_location_scope:
                scope_groups.append(ScopeGroup.LOCATION.value)
            if row.has_search_scope:
                scope_groups.append(ScopeGroup.SEARCH.value)
            result.append(
                CharacterInfo(
                    id=row.id,
                    name=row.name,
                    corporation_id=row.corporation_id,
                    alliance_id=row.alliance_id,
                    date_created=row.date_created,
                    scope_groups=scope_groups,
                )
            )
        return result

    async def get_primary_character_id(self, user_id: UUID) -> int | None:
        """Get user's primary character ID."""
        return await self.db_session.select_value(
            """SELECT primary_character_id FROM "user" WHERE id = $1""",
            user_id,
        )

    async def get_current_user(self, session_user: SessionUser) -> UserInfo:
        """Get current user with all linked characters."""
        characters = await self.get_user_characters(session_user.id)
        primary_character_id = await self.get_primary_character_id(session_user.id)
        is_owner = await self.acl_service.is_owner(session_user.id)
        is_admin = await self.acl_service.is_admin(session_user.id)

        # Determine if user can create maps
        # Privileged users (owner/admin) can always create maps
        # Regular users depend on the allow_map_creation setting
        if is_owner or is_admin:
            can_create_maps = True
        else:
            settings = await self.acl_service.get_settings()
            can_create_maps = settings.allow_map_creation if settings else True

        return UserInfo(
            id=session_user.id,
            primary_character_id=primary_character_id,
            characters=characters,
            is_owner=is_owner,
            is_admin=is_admin,
            can_create_maps=can_create_maps,
        )

    async def process_callback(
        self,
        code: str,
        code_verifier: str,
        current_user: SessionUser | None,
        is_linking: bool,
    ) -> CallbackResult:
        """Process SSO callback - exchange code, validate, and create/link user.

        Args:
            code: Authorization code from EVE SSO
            code_verifier: PKCE code verifier for token exchange
            current_user: Current session user (if authenticated)
            is_linking: Whether this is a character linking operation

        Returns:
            CallbackResult with user and character info for session

        Raises:
            ValueError: If linking but not logged in, or character belongs to another user
        """
        # Exchange code for tokens
        tokens = await self.sso_service.exchange_code(code, code_verifier)

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
            ACLDeniedError: If access is denied by instance ACL
        """
        existing_char = await self.get_character_by_id(char_info.character_id)

        # Fetch and upsert corporation/alliance from ESI
        # This makes them available for local entity search
        corporation_id, alliance_id = await self.fetch_and_upsert_affiliations(char_info.character_id)

        if is_linking:
            user_id = await self._handle_character_linking(
                char_info, current_user, existing_char, corporation_id, alliance_id
            )
        elif existing_char is not None:
            user_id = await self._handle_existing_user_login(existing_char)
        else:
            user_id = await self._handle_new_user_signup(char_info, corporation_id, alliance_id)

        # Check if location scope was removed (had it before, doesn't have it now)
        new_has_location = has_scope_group(char_info.scopes, ScopeGroup.LOCATION)
        if not new_has_location:
            previous_has_location = await self.db_session.select_value_or_none(
                "SELECT has_location_scope FROM refresh_token WHERE character_id = $1",
                char_info.character_id,
            )
            if previous_has_location:
                # Location scope was removed - clear cached location data
                await self._clear_location_cache(char_info.character_id)

        # Store encrypted refresh token with scope group flags
        await self.store_refresh_token(
            char_info.character_id,
            tokens.refresh_token,
            char_info.scopes,
            has_location_scope=new_has_location,
            has_search_scope=has_scope_group(char_info.scopes, ScopeGroup.SEARCH),
        )

        return user_id

    async def _handle_character_linking(
        self,
        char_info: SSOCharacterInfo,
        current_user: SessionUser | None,
        existing_char: CharacterUserInfo | None,
        corporation_id: int | None,
        alliance_id: int | None,
    ) -> UUID:
        """Handle linking an additional character to an existing user account.

        Args:
            char_info: Character info from JWT validation
            current_user: Current session user (must be authenticated)
            existing_char: Existing character record if any
            corporation_id: Character's corporation ID (may be None if ESI unavailable)
            alliance_id: Character's alliance ID if any

        Returns:
            The current user's ID

        Raises:
            ValueError: If not logged in, or character belongs to another user
        """
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
                corporation_id,
                alliance_id,
            )

        return current_user.id

    async def _handle_existing_user_login(self, existing_char: CharacterUserInfo) -> UUID:
        """Handle login for an existing user via known character.

        Args:
            existing_char: The existing character record

        Returns:
            The user ID associated with the character

        Raises:
            ACLDeniedError: If access is denied by instance ACL
        """
        has_access = await self.acl_service.check_user_access(existing_char.user_id)
        if not has_access:
            raise ACLDeniedError("Access denied by instance ACL")

        return existing_char.user_id

    async def _handle_new_user_signup(
        self,
        char_info: SSOCharacterInfo,
        corporation_id: int | None,
        alliance_id: int | None,
    ) -> UUID:
        """Handle signup for a new user.

        Creates a new user account and character, handles first-user ownership,
        and subscribes to default maps.

        Args:
            char_info: Character info from JWT validation
            corporation_id: Character's corporation ID (may be None if ESI unavailable)
            alliance_id: Character's alliance ID if any

        Returns:
            The newly created user ID

        Raises:
            ACLDeniedError: If signups are restricted by ACL
        """
        is_first_user = not await self.acl_service.has_owner()

        if not is_first_user:
            # Check ACL for new signups (before user exists)
            has_access = await self.acl_service.check_character_access(
                char_info.character_id,
                corporation_id,
                alliance_id,
            )
            if not has_access:
                raise ACLDeniedError("Signups are restricted by ACL")

        # Create new user and character
        user_id = await self.create_user()
        await self.create_character(
            char_info.character_id,
            user_id,
            char_info.character_name,
            corporation_id,
            alliance_id,
        )
        # Set first character as primary
        await self.set_primary_character(user_id, char_info.character_id)

        # If first user, make them the instance owner
        if is_first_user:
            await self.acl_service.set_owner(user_id)
            logger.info("First user %s set as instance owner", char_info.character_name)

        # Subscribe new user to default maps
        default_map_ids = await self.acl_service.get_default_map_ids()
        for map_id in default_map_ids:
            await self.db_session.execute(MAP_SUBSCRIPTION_INSERT, map_id, user_id)
        if default_map_ids:
            logger.info(
                "Subscribed new user %s to %d default maps",
                char_info.character_name,
                len(default_map_ids),
            )

        return user_id


async def provide_auth_service(
    db_session: AsyncDriverAdapterBase,
    sso_service: EveSSOService,
    encryption_service: EncryptionService,
    esi_client: ESIClient,
    location_cache: Valkey,
) -> AuthService:
    """Provide AuthService with injected dependencies."""
    acl_service = InstanceACLService(db_session)
    return AuthService(
        db_session,
        sso_service,
        encryption_service,
        esi_client,
        acl_service,
        location_cache,
    )
