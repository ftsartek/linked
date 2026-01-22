"""Admin API controller for instance management."""

from __future__ import annotations

from uuid import UUID

from litestar import Controller, Request, delete, get, patch, post
from litestar.di import Provide
from litestar.exceptions import ClientException, NotFoundException
from litestar.status_codes import HTTP_204_NO_CONTENT

from api.auth.guards import require_admin, require_auth, require_owner
from routes.admin.dependencies import (
    AddAdminRequest,
    AddAllianceACLRequest,
    AddCharacterACLRequest,
    AddCorporationACLRequest,
    AddDefaultSubscriptionRequest,
    AdminInfo,
    AdminListResponse,
    AllianceACLEntry,
    AllianceACLListResponse,
    CharacterACLEntry,
    CharacterACLListResponse,
    CorporationACLEntry,
    CorporationACLListResponse,
    DefaultSubscriptionInfo,
    DefaultSubscriptionListResponse,
    InstanceStatusResponse,
    PublicMapListResponse,
    TransferOwnershipRequest,
    UpdateInstanceRequest,
)
from routes.maps.service import MapService, provide_map_service
from services.instance_acl import InstanceACLService, provide_instance_acl_service


class AdminController(Controller):
    """Instance administration endpoints."""

    path = "/admin"
    guards = [require_auth]
    dependencies = {
        "acl_service": Provide(provide_instance_acl_service),
        "map_service": Provide(provide_map_service),
    }

    # ========================================================================
    # Instance Status & Settings
    # ========================================================================

    async def _get_instance_status(
        self,
        acl_service: InstanceACLService,
    ) -> InstanceStatusResponse:
        """Internal helper to build instance status response."""
        settings = await acl_service.get_settings()
        if settings is None:
            raise NotFoundException("Instance not initialized")

        counts = await acl_service.get_acl_counts()

        # Get owner's character name
        owner_name = await acl_service.db_session.select_value(
            """
            SELECT c.name FROM "user" u
            LEFT JOIN character c ON c.id = u.primary_character_id
            WHERE u.id = $1
            """,
            settings.owner_id,
        )

        return InstanceStatusResponse(
            owner_id=settings.owner_id,
            owner_name=owner_name,
            is_open=settings.is_open,
            allow_map_creation=settings.allow_map_creation,
            character_acl_count=counts.character_count,
            corporation_acl_count=counts.corporation_count,
            alliance_acl_count=counts.alliance_count,
            admin_count=counts.admin_count,
        )

    @get("/instance", guards=[require_admin])
    async def get_instance_status(
        self,
        acl_service: InstanceACLService,
    ) -> InstanceStatusResponse:
        """Get instance status including owner, open state, and ACL counts."""
        return await self._get_instance_status(acl_service)

    @patch("/instance", guards=[require_admin])
    async def update_instance_settings(
        self,
        acl_service: InstanceACLService,
        data: UpdateInstanceRequest,
    ) -> InstanceStatusResponse:
        """Update instance settings (is_open, allow_map_creation)."""
        if data.is_open is not None:
            await acl_service.set_open(data.is_open)
        if data.allow_map_creation is not None:
            await acl_service.set_allow_map_creation(data.allow_map_creation)
        return await self._get_instance_status(acl_service)

    @post("/instance/transfer", guards=[require_owner])
    async def transfer_ownership(
        self,
        request: Request,
        acl_service: InstanceACLService,
        data: TransferOwnershipRequest,
    ) -> InstanceStatusResponse:
        """Transfer instance ownership to another admin.

        Only the current owner can transfer ownership.
        The new owner must be an existing admin.
        The previous owner becomes an admin.
        """
        # Cannot transfer to self
        if data.new_owner_id == request.user.id:
            raise ClientException("Cannot transfer ownership to yourself")

        # Verify the new owner is currently an admin
        is_admin = await acl_service.is_admin(data.new_owner_id)
        if not is_admin:
            raise ClientException("Can only transfer ownership to an existing admin")

        # Remove new owner from admins (they're becoming owner)
        await acl_service.remove_admin(data.new_owner_id)

        # Transfer ownership
        previous_owner_id = request.user.id
        await acl_service.transfer_ownership(data.new_owner_id)

        # Add previous owner as admin
        await acl_service.add_admin(previous_owner_id, granted_by=data.new_owner_id)

        return await self._get_instance_status(acl_service)

    # ========================================================================
    # Admin Management
    # ========================================================================

    @get("/admins", guards=[require_admin])
    async def list_admins(
        self,
        acl_service: InstanceACLService,
    ) -> AdminListResponse:
        """List all instance admins."""
        admins = await acl_service.list_admins()
        return AdminListResponse(
            admins=[
                AdminInfo(
                    user_id=a.user_id,
                    character_id=a.character_id,
                    character_name=a.character_name,
                    granted_by=a.granted_by,
                    date_created=a.date_created,
                )
                for a in admins
            ]
        )

    @post("/admins", guards=[require_owner], status_code=HTTP_204_NO_CONTENT)
    async def add_admin(
        self,
        request: Request,
        acl_service: InstanceACLService,
        data: AddAdminRequest,
    ) -> None:
        """Add a user as admin. Only the owner can add admins."""
        # Verify user exists
        user_exists = await acl_service.db_session.select_value(
            """SELECT EXISTS(SELECT 1 FROM "user" WHERE id = $1)""",
            data.user_id,
        )
        if not user_exists:
            raise NotFoundException("User not found")

        # Cannot make owner an admin (they're already privileged)
        if await acl_service.is_owner(data.user_id):
            raise ClientException("Cannot add owner as admin")

        await acl_service.add_admin(data.user_id, granted_by=request.user.id)

    @delete("/admins/{user_id:uuid}", guards=[require_owner], status_code=HTTP_204_NO_CONTENT)
    async def remove_admin(
        self,
        acl_service: InstanceACLService,
        user_id: UUID,
    ) -> None:
        """Remove a user as admin. Only the owner can remove admins."""
        removed = await acl_service.remove_admin(user_id)
        if not removed:
            raise NotFoundException("Admin not found")

    # ========================================================================
    # Character ACL
    # ========================================================================

    @get("/acl/characters", guards=[require_admin])
    async def list_character_acl(
        self,
        acl_service: InstanceACLService,
    ) -> CharacterACLListResponse:
        """List all character ACL entries."""
        entries = await acl_service.list_character_acl()
        return CharacterACLListResponse(
            entries=[
                CharacterACLEntry(
                    character_id=e.character_id,
                    character_name=e.character_name,
                    added_by=e.added_by,
                    date_created=e.date_created,
                )
                for e in entries
            ]
        )

    @post("/acl/characters", guards=[require_admin], status_code=HTTP_204_NO_CONTENT)
    async def add_character_acl(
        self,
        request: Request,
        acl_service: InstanceACLService,
        data: AddCharacterACLRequest,
    ) -> None:
        """Add a character to the ACL."""
        await acl_service.add_character_acl(data.character_id, data.character_name, added_by=request.user.id)

    @delete(
        "/acl/characters/{character_id:int}",
        guards=[require_admin],
        status_code=HTTP_204_NO_CONTENT,
    )
    async def remove_character_acl(
        self,
        acl_service: InstanceACLService,
        character_id: int,
    ) -> None:
        """Remove a character from the ACL."""
        removed = await acl_service.remove_character_acl(character_id)
        if not removed:
            raise NotFoundException("Character ACL entry not found")

    # ========================================================================
    # Corporation ACL
    # ========================================================================

    @get("/acl/corporations", guards=[require_admin])
    async def list_corporation_acl(
        self,
        acl_service: InstanceACLService,
    ) -> CorporationACLListResponse:
        """List all corporation ACL entries."""
        entries = await acl_service.list_corporation_acl()
        return CorporationACLListResponse(
            entries=[
                CorporationACLEntry(
                    corporation_id=e.corporation_id,
                    corporation_name=e.corporation_name,
                    corporation_ticker=e.corporation_ticker,
                    added_by=e.added_by,
                    date_created=e.date_created,
                )
                for e in entries
            ]
        )

    @post("/acl/corporations", guards=[require_admin], status_code=HTTP_204_NO_CONTENT)
    async def add_corporation_acl(
        self,
        request: Request,
        acl_service: InstanceACLService,
        data: AddCorporationACLRequest,
    ) -> None:
        """Add a corporation to the ACL."""
        await acl_service.add_corporation_acl(
            data.corporation_id,
            data.corporation_name,
            data.corporation_ticker,
            added_by=request.user.id,
        )

    @delete(
        "/acl/corporations/{corporation_id:int}",
        guards=[require_admin],
        status_code=HTTP_204_NO_CONTENT,
    )
    async def remove_corporation_acl(
        self,
        acl_service: InstanceACLService,
        corporation_id: int,
    ) -> None:
        """Remove a corporation from the ACL."""
        removed = await acl_service.remove_corporation_acl(corporation_id)
        if not removed:
            raise NotFoundException("Corporation ACL entry not found")

    # ========================================================================
    # Alliance ACL
    # ========================================================================

    @get("/acl/alliances", guards=[require_admin])
    async def list_alliance_acl(
        self,
        acl_service: InstanceACLService,
    ) -> AllianceACLListResponse:
        """List all alliance ACL entries."""
        entries = await acl_service.list_alliance_acl()
        return AllianceACLListResponse(
            entries=[
                AllianceACLEntry(
                    alliance_id=e.alliance_id,
                    alliance_name=e.alliance_name,
                    alliance_ticker=e.alliance_ticker,
                    added_by=e.added_by,
                    date_created=e.date_created,
                )
                for e in entries
            ]
        )

    @post("/acl/alliances", guards=[require_admin], status_code=HTTP_204_NO_CONTENT)
    async def add_alliance_acl(
        self,
        request: Request,
        acl_service: InstanceACLService,
        data: AddAllianceACLRequest,
    ) -> None:
        """Add an alliance to the ACL."""
        await acl_service.add_alliance_acl(
            data.alliance_id,
            data.alliance_name,
            data.alliance_ticker,
            added_by=request.user.id,
        )

    @delete(
        "/acl/alliances/{alliance_id:int}",
        guards=[require_admin],
        status_code=HTTP_204_NO_CONTENT,
    )
    async def remove_alliance_acl(
        self,
        acl_service: InstanceACLService,
        alliance_id: int,
    ) -> None:
        """Remove an alliance from the ACL."""
        removed = await acl_service.remove_alliance_acl(alliance_id)
        if not removed:
            raise NotFoundException("Alliance ACL entry not found")

    # ========================================================================
    # Default Map Subscriptions
    # ========================================================================

    @get("/default-subscriptions", guards=[require_admin])
    async def list_default_subscriptions(
        self,
        acl_service: InstanceACLService,
    ) -> DefaultSubscriptionListResponse:
        """List all default map subscriptions."""
        entries = await acl_service.list_default_subscriptions()
        return DefaultSubscriptionListResponse(
            entries=[
                DefaultSubscriptionInfo(
                    map_id=e.map_id,
                    map_name=e.map_name,
                    added_by=e.added_by,
                    date_created=e.date_created,
                )
                for e in entries
            ]
        )

    @post("/default-subscriptions", guards=[require_admin], status_code=HTTP_204_NO_CONTENT)
    async def add_default_subscription(
        self,
        request: Request,
        acl_service: InstanceACLService,
        data: AddDefaultSubscriptionRequest,
    ) -> None:
        """Add a public map to default subscriptions.

        New users will be automatically subscribed to this map on signup.
        The map must be public.
        """
        # Verify the map exists and is public
        map_info = await acl_service.db_session.select_one_or_none(
            """
            SELECT id, is_public FROM map
            WHERE id = $1 AND date_deleted IS NULL
            """,
            data.map_id,
        )
        if map_info is None:
            raise NotFoundException("Map not found")
        if not map_info["is_public"]:
            raise ClientException("Only public maps can be added to default subscriptions")

        await acl_service.add_default_subscription(data.map_id, added_by=request.user.id)

    @delete(
        "/default-subscriptions/{map_id:uuid}",
        guards=[require_admin],
        status_code=HTTP_204_NO_CONTENT,
    )
    async def remove_default_subscription(
        self,
        acl_service: InstanceACLService,
        map_id: UUID,
    ) -> None:
        """Remove a map from default subscriptions."""
        removed = await acl_service.remove_default_subscription(map_id)
        if not removed:
            raise NotFoundException("Default subscription not found")

    # ========================================================================
    # Public Maps (Admin Access - No Filtering)
    # ========================================================================

    @get("/public-maps", guards=[require_admin])
    async def list_all_public_maps(
        self,
        map_service: MapService,
        limit: int = 20,
        offset: int = 0,
    ) -> PublicMapListResponse:
        """List ALL public maps without filtering (for admin use).

        Unlike the user-facing public maps endpoint, this does not filter out
        maps the admin already owns or has access to, allowing admins to add
        their own public maps as default subscriptions.
        """
        maps, total = await map_service.list_all_public_maps(limit=limit, offset=offset)
        return PublicMapListResponse(maps=maps, total=total)

    @get("/public-maps/search", guards=[require_admin])
    async def search_all_public_maps(
        self,
        map_service: MapService,
        q: str,
        limit: int = 20,
        offset: int = 0,
    ) -> PublicMapListResponse:
        """Search ALL public maps without filtering (for admin use).

        Unlike the user-facing search endpoint, this does not filter out
        maps the admin already owns or has access to.
        """
        maps, total = await map_service.search_all_public_maps(query=q, limit=limit, offset=offset)
        return PublicMapListResponse(maps=maps, total=total)
