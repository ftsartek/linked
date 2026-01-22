"""Instance ACL service.

Provides instance-level access control with owner/admin roles
and character/corporation/alliance-based ACLs.
"""

from __future__ import annotations

from uuid import UUID

from sqlspec import AsyncDriverAdapterBase

from database.models.default_subscription import (
    DELETE_STMT as DEFAULT_SUB_DELETE_STMT,
)
from database.models.default_subscription import (
    GET_MAP_IDS_STMT as DEFAULT_SUB_MAP_IDS_STMT,
)
from database.models.default_subscription import (
    INSERT_STMT as DEFAULT_SUB_INSERT_STMT,
)
from database.models.default_subscription import (
    LIST_STMT as DEFAULT_SUB_LIST_STMT,
)
from database.models.default_subscription import (
    DefaultMapSubscriptionWithName,
)
from database.models.instance_acl import (
    ALLIANCE_DELETE_STMT,
    ALLIANCE_INSERT_STMT,
    ALLIANCE_LIST_STMT,
    CHARACTER_DELETE_STMT,
    CHARACTER_INSERT_STMT,
    CHARACTER_LIST_STMT,
    CHECK_CHARACTER_ACCESS_STMT,
    CHECK_IS_OPEN_STMT,
    CHECK_IS_PRIVILEGED_STMT,
    CHECK_USER_ACCESS_STMT,
    CORPORATION_DELETE_STMT,
    CORPORATION_INSERT_STMT,
    CORPORATION_LIST_STMT,
    COUNT_ACL_ENTRIES_STMT,
    InstanceACLAllianceWithName,
    InstanceACLCharacterWithName,
    InstanceACLCorporationWithName,
    InstanceACLCounts,
)
from database.models.instance_admin import (
    CHECK_IS_ADMIN_STMT,
    InstanceAdminWithName,
)
from database.models.instance_admin import (
    DELETE_STMT as ADMIN_DELETE_STMT,
)
from database.models.instance_admin import (
    INSERT_STMT as ADMIN_INSERT_STMT,
)
from database.models.instance_admin import (
    LIST_STMT as ADMIN_LIST_STMT,
)
from database.models.instance_settings import (
    CHECK_HAS_OWNER_STMT,
    CHECK_IS_OWNER_STMT,
    UPDATE_ALLOW_MAP_CREATION_STMT,
    UPDATE_IS_OPEN_STMT,
    UPDATE_OWNER_STMT,
    InstanceSettings,
)
from database.models.instance_settings import (
    INSERT_STMT as SETTINGS_INSERT_STMT,
)
from database.models.instance_settings import (
    SELECT_STMT as SETTINGS_SELECT_STMT,
)


class InstanceACLService:
    """Instance-level access control service."""

    def __init__(self, db_session: AsyncDriverAdapterBase) -> None:
        self.db_session = db_session

    # ========================================================================
    # Owner Management
    # ========================================================================

    async def has_owner(self) -> bool:
        """Check if the instance has an owner (for first-user detection)."""
        return await self.db_session.select_value(CHECK_HAS_OWNER_STMT)

    async def get_settings(self) -> InstanceSettings | None:
        """Get instance settings including owner."""
        return await self.db_session.select_one_or_none(
            SETTINGS_SELECT_STMT,
            schema_type=InstanceSettings,
        )

    async def set_owner(self, user_id: UUID) -> InstanceSettings | None:
        """Set the initial owner (first user signup).

        Only works if no owner exists yet. Returns None if owner already set.
        """
        return await self.db_session.select_one_or_none(
            SETTINGS_INSERT_STMT,
            user_id,
            schema_type=InstanceSettings,
        )

    async def transfer_ownership(self, new_owner_id: UUID) -> InstanceSettings:
        """Transfer ownership to a new user.

        The previous owner becomes a regular user (not automatically admin).
        """
        return await self.db_session.select_one(
            UPDATE_OWNER_STMT,
            new_owner_id,
            schema_type=InstanceSettings,
        )

    async def is_owner(self, user_id: UUID) -> bool:
        """Check if user is the instance owner."""
        return await self.db_session.select_value(CHECK_IS_OWNER_STMT, user_id)

    # ========================================================================
    # Instance Settings
    # ========================================================================

    async def is_open(self) -> bool:
        """Check if the instance is open to new signups without ACL."""
        return await self.db_session.select_value(CHECK_IS_OPEN_STMT)

    async def set_open(self, is_open: bool) -> InstanceSettings:
        """Set whether the instance is open to new signups."""
        return await self.db_session.select_one(
            UPDATE_IS_OPEN_STMT,
            is_open,
            schema_type=InstanceSettings,
        )

    async def set_allow_map_creation(self, allow: bool) -> InstanceSettings:
        """Set whether non-admin users can create maps."""
        return await self.db_session.select_one(
            UPDATE_ALLOW_MAP_CREATION_STMT,
            allow,
            schema_type=InstanceSettings,
        )

    # ========================================================================
    # Admin Management
    # ========================================================================

    async def is_admin(self, user_id: UUID) -> bool:
        """Check if user is an instance admin (not owner)."""
        return await self.db_session.select_value(CHECK_IS_ADMIN_STMT, user_id)

    async def is_privileged(self, user_id: UUID) -> bool:
        """Check if user is owner OR admin (bypasses ACL)."""
        return await self.db_session.select_value(CHECK_IS_PRIVILEGED_STMT, user_id)

    async def add_admin(self, user_id: UUID, granted_by: UUID) -> bool:
        """Add a user as admin. Returns True if added, False if already admin."""
        result = await self.db_session.select_one_or_none(
            ADMIN_INSERT_STMT,
            user_id,
            granted_by,
        )
        return result is not None

    async def remove_admin(self, user_id: UUID) -> bool:
        """Remove a user as admin. Returns True if removed."""
        result = await self.db_session.execute(ADMIN_DELETE_STMT, user_id)
        return result.num_rows > 0

    async def list_admins(self) -> list[InstanceAdminWithName]:
        """List all admins with their character names."""
        return await self.db_session.select(
            ADMIN_LIST_STMT,
            schema_type=InstanceAdminWithName,
        )

    # ========================================================================
    # ACL Checks
    # ========================================================================

    async def check_user_access(self, user_id: UUID) -> bool:
        """Check if an existing user passes the ACL.

        Returns True if:
        - User is owner or admin (privileged)
        - Instance is open
        - Any of user's characters matches ACL (character/corp/alliance)
        """
        # Check if privileged first (owner or admin)
        if await self.is_privileged(user_id):
            return True

        # Check if instance is open
        if await self.is_open():
            return True

        # Check ACL
        return await self.db_session.select_value(CHECK_USER_ACCESS_STMT, user_id)

    async def check_character_access(
        self,
        character_id: int,
        corporation_id: int | None,
        alliance_id: int | None,
    ) -> bool:
        """Check if a character (with affiliations) passes the ACL.

        Used during signup to check before the user/character exists in DB.
        Does NOT check for privileged status (user doesn't exist yet).
        """
        # Check if instance is open
        if await self.is_open():
            return True

        # Check if any ACL entries exist - if none, this is first signup scenario
        counts = await self.get_acl_counts()
        if counts.character_count == 0 and counts.corporation_count == 0 and counts.alliance_count == 0:
            # No ACL entries and instance not open - only allow if no owner yet
            return not await self.has_owner()

        return await self.db_session.select_value(
            CHECK_CHARACTER_ACCESS_STMT,
            character_id,
            corporation_id,
            alliance_id,
        )

    # ========================================================================
    # Character ACL
    # ========================================================================

    async def add_character_acl(self, character_id: int, character_name: str, added_by: UUID) -> None:
        """Add a character to the ACL."""
        await self.db_session.execute(CHARACTER_INSERT_STMT, character_id, character_name, added_by)

    async def remove_character_acl(self, character_id: int) -> bool:
        """Remove a character from the ACL. Returns True if removed."""
        result = await self.db_session.execute(CHARACTER_DELETE_STMT, character_id)
        return result.num_rows > 0

    async def list_character_acl(self) -> list[InstanceACLCharacterWithName]:
        """List all character ACL entries with names."""
        return await self.db_session.select(
            CHARACTER_LIST_STMT,
            schema_type=InstanceACLCharacterWithName,
        )

    # ========================================================================
    # Corporation ACL
    # ========================================================================

    async def add_corporation_acl(
        self, corporation_id: int, corporation_name: str, corporation_ticker: str, added_by: UUID
    ) -> None:
        """Add a corporation to the ACL."""
        await self.db_session.execute(
            CORPORATION_INSERT_STMT, corporation_id, corporation_name, corporation_ticker, added_by
        )

    async def remove_corporation_acl(self, corporation_id: int) -> bool:
        """Remove a corporation from the ACL. Returns True if removed."""
        result = await self.db_session.execute(CORPORATION_DELETE_STMT, corporation_id)
        return result.num_rows > 0

    async def list_corporation_acl(self) -> list[InstanceACLCorporationWithName]:
        """List all corporation ACL entries with names."""
        return await self.db_session.select(
            CORPORATION_LIST_STMT,
            schema_type=InstanceACLCorporationWithName,
        )

    # ========================================================================
    # Alliance ACL
    # ========================================================================

    async def add_alliance_acl(
        self, alliance_id: int, alliance_name: str, alliance_ticker: str, added_by: UUID
    ) -> None:
        """Add an alliance to the ACL."""
        await self.db_session.execute(ALLIANCE_INSERT_STMT, alliance_id, alliance_name, alliance_ticker, added_by)

    async def remove_alliance_acl(self, alliance_id: int) -> bool:
        """Remove an alliance from the ACL. Returns True if removed."""
        result = await self.db_session.execute(ALLIANCE_DELETE_STMT, alliance_id)
        return result.num_rows > 0

    async def list_alliance_acl(self) -> list[InstanceACLAllianceWithName]:
        """List all alliance ACL entries with names."""
        return await self.db_session.select(
            ALLIANCE_LIST_STMT,
            schema_type=InstanceACLAllianceWithName,
        )

    # ========================================================================
    # Status
    # ========================================================================

    async def get_acl_counts(self) -> InstanceACLCounts:
        """Get counts of all ACL entries."""
        return await self.db_session.select_one(
            COUNT_ACL_ENTRIES_STMT,
            schema_type=InstanceACLCounts,
        )

    # ========================================================================
    # Default Map Subscriptions
    # ========================================================================

    async def list_default_subscriptions(self) -> list[DefaultMapSubscriptionWithName]:
        """List all default map subscriptions with map names."""
        return await self.db_session.select(
            DEFAULT_SUB_LIST_STMT,
            schema_type=DefaultMapSubscriptionWithName,
        )

    async def get_default_map_ids(self) -> list[UUID]:
        """Get IDs of all default subscription maps (for signup flow)."""
        rows = await self.db_session.select(DEFAULT_SUB_MAP_IDS_STMT)
        return [row["map_id"] for row in rows]

    async def add_default_subscription(self, map_id: UUID, added_by: UUID) -> bool:
        """Add a map to default subscriptions. Returns True if added."""
        result = await self.db_session.select_one_or_none(
            DEFAULT_SUB_INSERT_STMT,
            map_id,
            added_by,
        )
        return result is not None

    async def remove_default_subscription(self, map_id: UUID) -> bool:
        """Remove a map from default subscriptions. Returns True if removed."""
        result = await self.db_session.execute(DEFAULT_SUB_DELETE_STMT, map_id)
        return result.num_rows > 0


async def provide_instance_acl_service(
    db_session: AsyncDriverAdapterBase,
) -> InstanceACLService:
    """Provide InstanceACLService with injected dependencies."""
    return InstanceACLService(db_session)
