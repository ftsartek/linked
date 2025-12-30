from __future__ import annotations

from uuid import UUID

from litestar import Controller, Request, delete, get, patch, post
from litestar.di import Provide
from litestar.exceptions import NotAuthorizedException, NotFoundException
from litestar.status_codes import HTTP_204_NO_CONTENT

from api.auth.guards import require_auth
from routes.maps.dependencies import (
    AddAllianceAccessRequest,
    AddCorporationAccessRequest,
    AddUserAccessRequest,
    CreateLinkRequest,
    CreateMapRequest,
    CreateNodeRequest,
    EnrichedLinkInfo,
    EnrichedNodeInfo,
    EnrichedNodeInfoDTO,
    MapDetailResponse,
    MapDetailResponseDTO,
    MapInfo,
    MapListResponse,
    UpdateMapRequest,
)
from routes.maps.service import (
    MapService,
    provide_map_service,
)


class MapController(Controller):
    """Map management endpoints."""

    path = "/maps"
    guards = [require_auth]
    dependencies = {"map_service": Provide(provide_map_service, sync_to_thread=False)}

    @post("/")
    async def create_map(
        self,
        request: Request,
        map_service: MapService,
        data: CreateMapRequest,
    ) -> MapInfo:
        """Create a new map owned by the current user."""
        return await map_service.create_map(
            owner_id=request.user.id,
            name=data.name,
            description=data.description,
            is_public=data.is_public,
        )

    @get("/owned")
    async def list_owned(
        self,
        request: Request,
        map_service: MapService,
    ) -> MapListResponse:
        """List maps owned by the current user."""
        maps = await map_service.list_owned_maps(request.user.id)
        return MapListResponse(maps=maps)

    @get("/shared")
    async def list_shared(
        self,
        request: Request,
        map_service: MapService,
    ) -> MapListResponse:
        """List maps shared with the current user."""
        maps = await map_service.list_shared_maps(request.user.id)
        return MapListResponse(maps=maps)

    @get("/corporation")
    async def list_corporation(
        self,
        request: Request,
        map_service: MapService,
    ) -> MapListResponse:
        """List maps shared with the user's corporation."""
        ctx = await map_service.get_character_context(request.user.id)
        if ctx.corporation_id is None:
            return MapListResponse(maps=[])
        maps = await map_service.list_corporation_maps(ctx.corporation_id, ctx.user_id)
        return MapListResponse(maps=maps)

    @get("/alliance")
    async def list_alliance(
        self,
        request: Request,
        map_service: MapService,
    ) -> MapListResponse:
        """List maps shared with the user's alliance."""
        ctx = await map_service.get_character_context(request.user.id)
        if ctx.alliance_id is None:
            return MapListResponse(maps=[])
        maps = await map_service.list_alliance_maps(ctx.alliance_id, ctx.user_id, ctx.corporation_id)
        return MapListResponse(maps=maps)

    @get("/{map_id:uuid}", return_dto=MapDetailResponseDTO)
    async def load_map(
        self,
        request: Request,
        map_service: MapService,
        map_id: UUID,
    ) -> MapDetailResponse:
        """Load a map with all its nodes and links."""
        ctx = await map_service.get_character_context(request.user.id)

        has_access = await map_service.can_access_map(
            map_id=map_id,
            user_id=ctx.user_id,
            corporation_id=ctx.corporation_id,
            alliance_id=ctx.alliance_id,
        )
        if not has_access:
            raise NotAuthorizedException("You do not have access to this map")

        map_info = await map_service.get_map(map_id)
        if map_info is None:
            raise NotFoundException("Map not found")

        map_info.edit_access = await map_service.has_edit_access(
            map_id=map_id,
            user_id=ctx.user_id,
            corporation_id=ctx.corporation_id,
            alliance_id=ctx.alliance_id,
        )

        nodes = await map_service.get_map_nodes(map_id)
        links = await map_service.get_map_links(map_id)

        return MapDetailResponse(map=map_info, nodes=nodes, links=links)

    @patch("/{map_id:uuid}")
    async def update_map(
        self,
        request: Request,
        map_service: MapService,
        map_id: UUID,
        data: UpdateMapRequest,
    ) -> MapInfo:
        """Update a map. Only the owner can update."""
        if not await map_service.is_owner(map_id, request.user.id):
            raise NotAuthorizedException("Only the owner can update this map")

        result = await map_service.update_map(
            map_id=map_id,
            name=data.name,
            description=data.description,
            is_public=data.is_public,
        )
        if result is None:
            raise NotFoundException("Map not found")
        return result

    @delete("/{map_id:uuid}", status_code=HTTP_204_NO_CONTENT)
    async def delete_map(
        self,
        request: Request,
        map_service: MapService,
        map_id: UUID,
    ) -> None:
        """Delete a map. Only the owner can delete."""
        if not await map_service.is_owner(map_id, request.user.id):
            raise NotAuthorizedException("Only the owner can delete this map")

        deleted = await map_service.delete_map(map_id)
        if not deleted:
            raise NotFoundException("Map not found")

    # User access management

    @post("/{map_id:uuid}/users", status_code=HTTP_204_NO_CONTENT)
    async def add_user_access(
        self,
        request: Request,
        map_service: MapService,
        map_id: UUID,
        data: AddUserAccessRequest,
    ) -> None:
        """Add user access to a map. Only the owner can add users."""
        if not await map_service.is_owner(map_id, request.user.id):
            raise NotAuthorizedException("Only the owner can manage map access")

        await map_service.add_user_access(map_id, data.user_id, data.read_only)

    @delete("/{map_id:uuid}/users/{user_id:uuid}", status_code=HTTP_204_NO_CONTENT)
    async def remove_user_access(
        self,
        request: Request,
        map_service: MapService,
        map_id: UUID,
        user_id: UUID,
    ) -> None:
        """Remove user access from a map. Only the owner can remove users."""
        if not await map_service.is_owner(map_id, request.user.id):
            raise NotAuthorizedException("Only the owner can manage map access")

        await map_service.remove_user_access(map_id, user_id)

    # Corporation access management

    @post("/{map_id:uuid}/corporations", status_code=HTTP_204_NO_CONTENT)
    async def add_corporation_access(
        self,
        request: Request,
        map_service: MapService,
        map_id: UUID,
        data: AddCorporationAccessRequest,
    ) -> None:
        """Add corporation access to a map. Only the owner can add corporations."""
        if not await map_service.is_owner(map_id, request.user.id):
            raise NotAuthorizedException("Only the owner can manage map access")

        await map_service.add_corporation_access(map_id, data.corporation_id, data.read_only)

    @delete("/{map_id:uuid}/corporations/{corporation_id:int}", status_code=HTTP_204_NO_CONTENT)
    async def remove_corporation_access(
        self,
        request: Request,
        map_service: MapService,
        map_id: UUID,
        corporation_id: int,
    ) -> None:
        """Remove corporation access from a map. Only the owner can remove corporations."""
        if not await map_service.is_owner(map_id, request.user.id):
            raise NotAuthorizedException("Only the owner can manage map access")

        await map_service.remove_corporation_access(map_id, corporation_id)

    # Alliance access management

    @post("/{map_id:uuid}/alliances", status_code=HTTP_204_NO_CONTENT)
    async def add_alliance_access(
        self,
        request: Request,
        map_service: MapService,
        map_id: UUID,
        data: AddAllianceAccessRequest,
    ) -> None:
        """Add alliance access to a map. Only the owner can add alliances."""
        if not await map_service.is_owner(map_id, request.user.id):
            raise NotAuthorizedException("Only the owner can manage map access")

        await map_service.add_alliance_access(map_id, data.alliance_id, data.read_only)

    @delete("/{map_id:uuid}/alliances/{alliance_id:int}", status_code=HTTP_204_NO_CONTENT)
    async def remove_alliance_access(
        self,
        request: Request,
        map_service: MapService,
        map_id: UUID,
        alliance_id: int,
    ) -> None:
        """Remove alliance access from a map. Only the owner can remove alliances."""
        if not await map_service.is_owner(map_id, request.user.id):
            raise NotAuthorizedException("Only the owner can manage map access")

        await map_service.remove_alliance_access(map_id, alliance_id)

    # Node management

    @post("/{map_id:uuid}/nodes", return_dto=EnrichedNodeInfoDTO)
    async def create_node(
        self,
        request: Request,
        map_service: MapService,
        map_id: UUID,
        data: CreateNodeRequest,
    ) -> EnrichedNodeInfo:
        """Create a new node on the map."""
        ctx = await map_service.get_character_context(request.user.id)

        has_access = await map_service.can_access_map(
            map_id=map_id,
            user_id=ctx.user_id,
            corporation_id=ctx.corporation_id,
            alliance_id=ctx.alliance_id,
        )
        if not has_access:
            raise NotAuthorizedException("You do not have access to this map")

        return await map_service.create_node(
            map_id=map_id,
            system_id=data.system_id,
            pos_x=data.pos_x,
            pos_y=data.pos_y,
        )

    # Link management

    @post("/{map_id:uuid}/links")
    async def create_link(
        self,
        request: Request,
        map_service: MapService,
        map_id: UUID,
        data: CreateLinkRequest,
    ) -> EnrichedLinkInfo:
        """Create a new link between nodes."""
        ctx = await map_service.get_character_context(request.user.id)

        has_access = await map_service.can_access_map(
            map_id=map_id,
            user_id=ctx.user_id,
            corporation_id=ctx.corporation_id,
            alliance_id=ctx.alliance_id,
        )
        if not has_access:
            raise NotAuthorizedException("You do not have access to this map")

        return await map_service.create_link(
            map_id=map_id,
            source_node_id=data.source_node_id,
            target_node_id=data.target_node_id,
            wormhole_id=data.wormhole_id,
        )
