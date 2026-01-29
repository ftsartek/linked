from __future__ import annotations

from uuid import UUID

from litestar import Controller, Request, delete, get, patch, post
from litestar.channels import ChannelsPlugin
from litestar.di import Provide
from litestar.dto import DTOData
from litestar.exceptions import ClientException, NotAuthorizedException, NotFoundException
from litestar.params import Parameter
from litestar.response import ServerSentEvent
from litestar.status_codes import HTTP_202_ACCEPTED, HTTP_204_NO_CONTENT, HTTP_409_CONFLICT
from valkey.asyncio import Valkey

from api.auth.guards import require_acl_access, require_auth
from api.di.valkey import provide_location_cache
from routes.maps.dependencies import (
    ERR_LINK_NODE_MISMATCH,
    ERR_LINK_NOT_FOUND,
    ERR_MAP_CREATION_DISABLED,
    ERR_MAP_NO_ACCESS,
    ERR_MAP_NO_EDIT_ACCESS,
    ERR_MAP_NOT_FOUND,
    ERR_MAP_OWNER_ONLY,
    ERR_NODE_LOCKED,
    ERR_NODE_NOT_FOUND,
    ERR_NOTE_NOT_FOUND,
    ERR_SIGNATURE_NOT_FOUND,
    AddAllianceAccessRequest,
    AddCharacterAccessRequest,
    AddCorporationAccessRequest,
    BulkCreateSignatureRequest,
    BulkSignatureResponse,
    CreateConnectionFromSignatureRequest,
    CreateConnectionFromSignatureResponse,
    CreateLinkRequest,
    CreateLinkResponse,
    CreateMapRequest,
    CreateNodeRequest,
    CreateNodeResponse,
    CreateNoteRequest,
    CreateNoteResponse,
    CreateSignatureRequest,
    CreateSignatureResponse,
    DeleteLinkResponse,
    DeleteMapResponse,
    DeleteNodeResponse,
    DeleteNoteResponse,
    DeleteSignatureResponse,
    EnrichedLinkInfo,
    EnrichedNodeInfo,
    EnrichedNodeSourceData,
    EnrichedSignatureInfo,
    MapAccessResponse,
    MapDetailResponse,
    MapInfo,
    MapListResponse,
    NodeConnectionsResponse,
    NodeSignaturesResponse,
    PublicMapListResponse,
    SetLinkTypeRequest,
    SubscriptionResponse,
    SystemNotesResponse,
    UpdateLinkRequest,
    UpdateLinkResponse,
    UpdateMapRequest,
    UpdateNodeLockedRequest,
    UpdateNodePositionRequest,
    UpdateNodeResponse,
    UpdateNodeSystemRequest,
    UpdateNoteDTO,
    UpdateNoteRequest,
    UpdateNoteResponse,
    UpdateSignatureDTO,
    UpdateSignatureRequest,
    UpdateSignatureResponse,
)
from routes.maps.publisher import EventPublisher, provide_event_publisher
from routes.maps.queries import (
    GET_LINK_ENRICHED,
    GET_NODE_ENRICHED,
    GET_SIGNATURE_ENRICHED,
)
from routes.maps.service import (
    MapService,
    NodeLockedError,
    provide_map_service,
)
from services.instance_acl import InstanceACLService, provide_instance_acl_service
from utils.valkey import NamespacedValkey


class MapController(Controller):
    """Map management endpoints."""

    path = "/maps"
    guards = [require_auth, require_acl_access]
    dependencies = {
        "map_service": Provide(provide_map_service),
        "event_publisher": Provide(provide_event_publisher),
        "acl_service": Provide(provide_instance_acl_service),
        "location_cache": Provide(provide_location_cache),
    }

    @post("/")
    async def create_map(
        self,
        request: Request,
        map_service: MapService,
        acl_service: InstanceACLService,
        data: CreateMapRequest,
    ) -> MapInfo:
        """Create a new map owned by the current user."""
        # Check if map creation is allowed for this user
        is_privileged = await acl_service.is_privileged(request.user.id)
        if not is_privileged:
            settings = await acl_service.get_settings()
            if settings is None or not settings.allow_map_creation:
                raise NotAuthorizedException(ERR_MAP_CREATION_DISABLED)

        return await map_service.create_map(
            owner_id=request.user.id,
            name=data.name,
            description=data.description,
            is_public=data.is_public,
            public_read_only=data.public_read_only,
            edge_type=data.edge_type,
            rankdir=data.rankdir,
            auto_layout=data.auto_layout,
            node_sep=data.node_sep,
            rank_sep=data.rank_sep,
            location_tracking_enabled=data.location_tracking_enabled,
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

    # Public map browsing and subscriptions

    @get("/public")
    async def list_public(
        self,
        request: Request,
        map_service: MapService,
        limit: int = 20,
        offset: int = 0,
    ) -> PublicMapListResponse:
        """List public maps ordered by popularity (subscription count).

        Excludes maps the user already has access to via ownership, subscription, or explicit shares.
        """
        ctx = await map_service.get_character_context(request.user.id)
        maps, total = await map_service.list_public_maps(
            user_id=request.user.id,
            corporation_id=ctx.corporation_id,
            alliance_id=ctx.alliance_id,
            limit=min(limit, 100),  # Cap at 100
            offset=offset,
        )
        return PublicMapListResponse(
            maps=maps,
            total=total,
            limit=limit,
            offset=offset,
        )

    @get("/public/search")
    async def search_public(
        self,
        request: Request,
        map_service: MapService,
        q: str = "",
        limit: int = 20,
        offset: int = 0,
    ) -> PublicMapListResponse:
        """Search public maps by name or description.

        Excludes maps the user already has access to via ownership, subscription, or explicit shares.
        """
        if len(q) < 2:
            return PublicMapListResponse(maps=[], total=0, limit=limit, offset=offset)

        ctx = await map_service.get_character_context(request.user.id)
        maps, total = await map_service.search_public_maps(
            user_id=request.user.id,
            corporation_id=ctx.corporation_id,
            alliance_id=ctx.alliance_id,
            query=q,
            limit=min(limit, 100),
            offset=offset,
        )
        return PublicMapListResponse(
            maps=maps,
            total=total,
            limit=limit,
            offset=offset,
        )

    @get("/subscribed")
    async def list_subscribed(
        self,
        request: Request,
        map_service: MapService,
    ) -> MapListResponse:
        """List maps the current user has subscribed to."""
        maps = await map_service.list_subscribed_maps(request.user.id)
        return MapListResponse(maps=maps)

    @post("/{map_id:uuid}/subscribe")
    async def subscribe_to_map(
        self,
        request: Request,
        map_service: MapService,
        map_id: UUID,
    ) -> SubscriptionResponse:
        """Subscribe to a public map."""
        try:
            return await map_service.subscribe_to_map(map_id, request.user.id)
        except ValueError as e:
            raise NotFoundException(str(e)) from e

    @delete("/{map_id:uuid}/subscribe", status_code=200)
    async def unsubscribe_from_map(
        self,
        request: Request,
        map_service: MapService,
        map_id: UUID,
    ) -> SubscriptionResponse:
        """Unsubscribe from a public map."""
        return await map_service.unsubscribe_from_map(map_id, request.user.id)

    @get("/{map_id:uuid}")
    async def load_map(
        self,
        request: Request,
        map_service: MapService,
        valkey_client: Valkey,
        location_cache: NamespacedValkey,
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
            raise NotAuthorizedException(ERR_MAP_NO_ACCESS)

        # IMPORTANT: Fetch event ID BEFORE loading map data
        # This ensures we never miss events (may replay one, but that's safe with duplicate checks)
        last_event_id_bytes = await valkey_client.get(f"map_event_seq:{map_id}")
        last_event_id = last_event_id_bytes.decode() if last_event_id_bytes else None

        map_info = await map_service.get_map(map_id)
        if map_info is None:
            raise NotFoundException(ERR_MAP_NOT_FOUND)

        map_info.edit_access = await map_service.has_edit_access(
            map_id=map_id,
            user_id=ctx.user_id,
            corporation_id=ctx.corporation_id,
            alliance_id=ctx.alliance_id,
        )

        nodes = await map_service.get_map_nodes(map_id)
        links = await map_service.get_map_links(map_id)

        # Populate character locations on nodes if location tracking is enabled
        if map_info.location_tracking_enabled:
            await map_service.populate_node_character_locations(map_id, nodes, location_cache)

        return MapDetailResponse(map=map_info, nodes=nodes, links=links, last_event_id=last_event_id)

    @get("/{map_id:uuid}/events")
    async def subscribe_events(
        self,
        request: Request,
        map_service: MapService,
        valkey_client: Valkey,
        map_id: UUID,
        channels: ChannelsPlugin,
        last_event_id: str | None = None,
    ) -> ServerSentEvent:
        """Subscribe to real-time map events via SSE.

        Returns a stream of events for map changes (nodes, links, map updates).
        History of up to 50 recent events is sent on initial connection.

        Supports resumption via either:
        - The SSE `Last-Event-ID` header (automatic on reconnect)
        - The `last_event_id` query parameter (for initial connection after map load)

        Events before the provided ID will be skipped.

        Access revocation events are intercepted and will terminate the stream
        if the user no longer has access to the map.
        """
        ctx = await map_service.get_character_context(request.user.id)

        has_access = await map_service.can_access_map(
            map_id=map_id,
            user_id=ctx.user_id,
            corporation_id=ctx.corporation_id,
            alliance_id=ctx.alliance_id,
        )
        if not has_access:
            raise NotAuthorizedException(ERR_MAP_NO_ACCESS)

        # Support both query param (initial connection) and header (SSE auto-reconnect)
        last_event_id = last_event_id or request.headers.get("Last-Event-ID")

        return await map_service.subscribe_events(
            map_id=map_id,
            ctx=ctx,
            channels=channels,
            valkey_client=valkey_client,
            last_event_id=last_event_id,
        )

    @patch("/{map_id:uuid}")
    async def update_map(
        self,
        request: Request,
        map_service: MapService,
        event_publisher: EventPublisher,
        map_id: UUID,
        data: UpdateMapRequest,
    ) -> MapInfo:
        """Update a map. Only the owner can update."""
        if not await map_service.is_owner(map_id, request.user.id):
            raise NotAuthorizedException(ERR_MAP_OWNER_ONLY)

        result = await map_service.update_map(
            map_id=map_id,
            name=data.name,
            description=data.description,
            is_public=data.is_public,
            public_read_only=data.public_read_only,
            edge_type=data.edge_type,
            rankdir=data.rankdir,
            auto_layout=data.auto_layout,
            node_sep=data.node_sep,
            rank_sep=data.rank_sep,
            location_tracking_enabled=data.location_tracking_enabled,
        )
        if result is None:
            raise NotFoundException(ERR_MAP_NOT_FOUND)

        await event_publisher.map_updated(map_id, result, user_id=request.user.id)
        return result

    @delete("/{map_id:uuid}", status_code=HTTP_202_ACCEPTED)
    async def delete_map(
        self,
        request: Request,
        map_service: MapService,
        event_publisher: EventPublisher,
        map_id: UUID,
    ) -> DeleteMapResponse:
        """Soft-delete a map and all its nodes/links. Only the owner can delete."""
        if not await map_service.is_owner(map_id, request.user.id):
            raise NotAuthorizedException(ERR_MAP_OWNER_ONLY)

        result = await map_service.delete_map(map_id)
        if result is None:
            raise NotFoundException(ERR_MAP_NOT_FOUND)

        await event_publisher.map_deleted(map_id, result, user_id=request.user.id)
        return result

    # Access management

    @get("/{map_id:uuid}/access")
    async def get_map_access(
        self,
        request: Request,
        map_service: MapService,
        map_id: UUID,
    ) -> MapAccessResponse:
        """Get all access entries for a map. Only the owner can view access."""
        if not await map_service.is_owner(map_id, request.user.id):
            raise NotAuthorizedException(ERR_MAP_OWNER_ONLY)

        return await map_service.get_map_access(map_id)

    @post("/{map_id:uuid}/characters", status_code=HTTP_204_NO_CONTENT)
    async def add_character_access(
        self,
        request: Request,
        map_service: MapService,
        event_publisher: EventPublisher,
        map_id: UUID,
        data: AddCharacterAccessRequest,
    ) -> None:
        """Add character access to a map. Only the owner can add characters."""
        if not await map_service.is_owner(map_id, request.user.id):
            raise NotAuthorizedException(ERR_MAP_OWNER_ONLY)

        await map_service.add_character_access(map_id, data.character_id, data.read_only)
        await event_publisher.access_character_granted(
            map_id, data.character_id, data.read_only, user_id=request.user.id
        )

    @delete("/{map_id:uuid}/characters/{character_id:int}", status_code=HTTP_204_NO_CONTENT)
    async def remove_character_access(
        self,
        request: Request,
        map_service: MapService,
        event_publisher: EventPublisher,
        map_id: UUID,
        character_id: int,
    ) -> None:
        """Remove character access from a map. Only the owner can remove characters."""
        if not await map_service.is_owner(map_id, request.user.id):
            raise NotAuthorizedException(ERR_MAP_OWNER_ONLY)

        await map_service.remove_character_access(map_id, character_id)
        await event_publisher.access_character_revoked(map_id, character_id, user_id=request.user.id)

    # Corporation access management

    @post("/{map_id:uuid}/corporations", status_code=HTTP_204_NO_CONTENT)
    async def add_corporation_access(
        self,
        request: Request,
        map_service: MapService,
        event_publisher: EventPublisher,
        map_id: UUID,
        data: AddCorporationAccessRequest,
    ) -> None:
        """Add corporation access to a map. Only the owner can add corporations."""
        if not await map_service.is_owner(map_id, request.user.id):
            raise NotAuthorizedException(ERR_MAP_OWNER_ONLY)

        await map_service.add_corporation_access(map_id, data.corporation_id, data.read_only)
        await event_publisher.access_corporation_granted(
            map_id, data.corporation_id, data.read_only, user_id=request.user.id
        )

    @delete("/{map_id:uuid}/corporations/{corporation_id:int}", status_code=HTTP_204_NO_CONTENT)
    async def remove_corporation_access(
        self,
        request: Request,
        map_service: MapService,
        event_publisher: EventPublisher,
        map_id: UUID,
        corporation_id: int,
    ) -> None:
        """Remove corporation access from a map. Only the owner can remove corporations."""
        if not await map_service.is_owner(map_id, request.user.id):
            raise NotAuthorizedException(ERR_MAP_OWNER_ONLY)

        await map_service.remove_corporation_access(map_id, corporation_id)
        await event_publisher.access_corporation_revoked(map_id, corporation_id, user_id=request.user.id)

    # Alliance access management

    @post("/{map_id:uuid}/alliances", status_code=HTTP_204_NO_CONTENT)
    async def add_alliance_access(
        self,
        request: Request,
        map_service: MapService,
        event_publisher: EventPublisher,
        map_id: UUID,
        data: AddAllianceAccessRequest,
    ) -> None:
        """Add alliance access to a map. Only the owner can add alliances."""
        if not await map_service.is_owner(map_id, request.user.id):
            raise NotAuthorizedException(ERR_MAP_OWNER_ONLY)

        await map_service.add_alliance_access(map_id, data.alliance_id, data.read_only)
        await event_publisher.access_alliance_granted(map_id, data.alliance_id, data.read_only, user_id=request.user.id)

    @delete("/{map_id:uuid}/alliances/{alliance_id:int}", status_code=HTTP_204_NO_CONTENT)
    async def remove_alliance_access(
        self,
        request: Request,
        map_service: MapService,
        event_publisher: EventPublisher,
        map_id: UUID,
        alliance_id: int,
    ) -> None:
        """Remove alliance access from a map. Only the owner can remove alliances."""
        if not await map_service.is_owner(map_id, request.user.id):
            raise NotAuthorizedException(ERR_MAP_OWNER_ONLY)

        await map_service.remove_alliance_access(map_id, alliance_id)
        await event_publisher.access_alliance_revoked(map_id, alliance_id, user_id=request.user.id)

    # Node management
    @post("/{map_id:uuid}/nodes")
    async def create_node(
        self,
        request: Request,
        map_service: MapService,
        event_publisher: EventPublisher,
        map_id: UUID,
        data: CreateNodeRequest,
    ) -> CreateNodeResponse:
        """Create a new node on the map. Full data delivered via SSE."""
        ctx = await map_service.get_character_context(request.user.id)

        has_edit_access = await map_service.has_edit_access(
            map_id=map_id,
            user_id=ctx.user_id,
            corporation_id=ctx.corporation_id,
            alliance_id=ctx.alliance_id,
        )
        if not has_edit_access:
            raise NotAuthorizedException(ERR_MAP_NO_EDIT_ACCESS)

        result = await map_service.create_node(
            map_id=map_id,
            system_id=data.system_id,
            pos_x=data.pos_x,
            pos_y=data.pos_y,
        )
        await event_publisher.node_created(map_id, result, user_id=request.user.id)
        return CreateNodeResponse(node_id=result.id)

    @patch("/{map_id:uuid}/nodes/{node_id:uuid}/position")
    async def update_node_position(
        self,
        request: Request,
        map_service: MapService,
        event_publisher: EventPublisher,
        map_id: UUID,
        node_id: UUID,
        data: UpdateNodePositionRequest,
    ) -> UpdateNodeResponse:
        """Update a node's position on the map. Full data delivered via SSE."""
        ctx = await map_service.get_character_context(request.user.id)

        has_edit_access = await map_service.has_edit_access(
            map_id=map_id,
            user_id=ctx.user_id,
            corporation_id=ctx.corporation_id,
            alliance_id=ctx.alliance_id,
        )
        if not has_edit_access:
            raise NotAuthorizedException(ERR_MAP_NO_EDIT_ACCESS)

        try:
            result = await map_service.update_node_position(
                map_id=map_id,
                node_id=node_id,
                pos_x=data.pos_x,
                pos_y=data.pos_y,
            )
        except NodeLockedError:
            raise ClientException(ERR_NODE_LOCKED, status_code=HTTP_409_CONFLICT)
        if result is None:
            raise NotFoundException(ERR_NODE_NOT_FOUND)

        await event_publisher.node_updated(map_id, result, user_id=request.user.id)
        return UpdateNodeResponse(node_id=result.id)

    @patch("/{map_id:uuid}/nodes/{node_id:uuid}/system")
    async def update_node_system(
        self,
        request: Request,
        map_service: MapService,
        event_publisher: EventPublisher,
        map_id: UUID,
        node_id: UUID,
        data: UpdateNodeSystemRequest,
    ) -> UpdateNodeResponse:
        """Update a node's system. Full data delivered via SSE."""
        ctx = await map_service.get_character_context(request.user.id)

        has_edit_access = await map_service.has_edit_access(
            map_id=map_id,
            user_id=ctx.user_id,
            corporation_id=ctx.corporation_id,
            alliance_id=ctx.alliance_id,
        )
        if not has_edit_access:
            raise NotAuthorizedException(ERR_MAP_NO_EDIT_ACCESS)

        try:
            result = await map_service.update_node_system(
                map_id=map_id,
                node_id=node_id,
                system_id=data.system_id,
            )
        except NodeLockedError:
            raise ClientException(ERR_NODE_LOCKED, status_code=HTTP_409_CONFLICT)
        if result is None:
            raise NotFoundException(ERR_NODE_NOT_FOUND)

        await event_publisher.node_updated(map_id, result, user_id=request.user.id)
        return UpdateNodeResponse(node_id=result.id)

    @patch("/{map_id:uuid}/nodes/{node_id:uuid}/locked")
    async def update_node_locked(
        self,
        request: Request,
        map_service: MapService,
        event_publisher: EventPublisher,
        map_id: UUID,
        node_id: UUID,
        data: UpdateNodeLockedRequest,
    ) -> UpdateNodeResponse:
        """Update a node's locked status. Only the owner can lock/unlock nodes."""
        if not await map_service.is_owner(map_id, request.user.id):
            raise NotAuthorizedException(ERR_MAP_OWNER_ONLY)

        result = await map_service.update_node_locked(
            map_id=map_id,
            node_id=node_id,
            locked=data.locked,
        )
        if result is None:
            raise NotFoundException(ERR_NODE_NOT_FOUND)

        await event_publisher.node_updated(map_id, result, user_id=request.user.id)
        return UpdateNodeResponse(node_id=result.id)

    @delete("/{map_id:uuid}/nodes/{node_id:uuid}", status_code=HTTP_202_ACCEPTED)
    async def delete_node(
        self,
        request: Request,
        map_service: MapService,
        event_publisher: EventPublisher,
        map_id: UUID,
        node_id: UUID,
    ) -> DeleteNodeResponse:
        """Soft-delete a node and its connected links from the map."""
        ctx = await map_service.get_character_context(request.user.id)

        has_edit_access = await map_service.has_edit_access(
            map_id=map_id,
            user_id=ctx.user_id,
            corporation_id=ctx.corporation_id,
            alliance_id=ctx.alliance_id,
        )
        if not has_edit_access:
            raise NotAuthorizedException(ERR_MAP_NO_EDIT_ACCESS)

        result = await map_service.delete_node(map_id, node_id)
        if result is None:
            raise NotFoundException(ERR_NODE_NOT_FOUND)

        await event_publisher.node_deleted(map_id, result, user_id=request.user.id)
        return result

    # Link management

    @post("/{map_id:uuid}/links")
    async def create_link(
        self,
        request: Request,
        map_service: MapService,
        event_publisher: EventPublisher,
        map_id: UUID,
        data: CreateLinkRequest,
    ) -> CreateLinkResponse:
        """Create a new link between nodes. Full data delivered via SSE."""
        ctx = await map_service.get_character_context(request.user.id)

        has_edit_access = await map_service.has_edit_access(
            map_id=map_id,
            user_id=ctx.user_id,
            corporation_id=ctx.corporation_id,
            alliance_id=ctx.alliance_id,
        )
        if not has_edit_access:
            raise NotAuthorizedException(ERR_MAP_NO_EDIT_ACCESS)

        result = await map_service.create_link(
            map_id=map_id,
            source_node_id=data.source_node_id,
            target_node_id=data.target_node_id,
            wormhole_id=data.wormhole_id,
        )
        await event_publisher.link_created(map_id, result, user_id=request.user.id)
        return CreateLinkResponse(link_id=result.id)

    @patch("/{map_id:uuid}/links/{link_id:uuid}")
    async def update_link(
        self,
        request: Request,
        map_service: MapService,
        event_publisher: EventPublisher,
        map_id: UUID,
        link_id: UUID,
        data: UpdateLinkRequest,
    ) -> UpdateLinkResponse:
        """Update a link between nodes. Full data delivered via SSE."""
        ctx = await map_service.get_character_context(request.user.id)

        has_edit_access = await map_service.has_edit_access(
            map_id=map_id,
            user_id=ctx.user_id,
            corporation_id=ctx.corporation_id,
            alliance_id=ctx.alliance_id,
        )
        if not has_edit_access:
            raise NotAuthorizedException(ERR_MAP_NO_EDIT_ACCESS)

        result = await map_service.update_link(
            map_id=map_id,
            link_id=link_id,
            wormhole_id=data.wormhole_id,
            lifetime_status=data.lifetime_status,
            mass_usage=data.mass_usage,
            reverse=data.reverse,
        )
        if result is None:
            raise NotFoundException(ERR_LINK_NOT_FOUND)

        await event_publisher.link_updated(map_id, result, user_id=request.user.id)
        return UpdateLinkResponse(link_id=result.id)

    @delete("/{map_id:uuid}/links/{link_id:uuid}", status_code=HTTP_202_ACCEPTED)
    async def delete_link(
        self,
        request: Request,
        map_service: MapService,
        event_publisher: EventPublisher,
        map_id: UUID,
        link_id: UUID,
    ) -> DeleteLinkResponse:
        """Soft-delete a link from the map."""
        ctx = await map_service.get_character_context(request.user.id)

        has_edit_access = await map_service.has_edit_access(
            map_id=map_id,
            user_id=ctx.user_id,
            corporation_id=ctx.corporation_id,
            alliance_id=ctx.alliance_id,
        )
        if not has_edit_access:
            raise NotAuthorizedException(ERR_MAP_NO_EDIT_ACCESS)

        result = await map_service.delete_link(map_id, link_id)
        if result is None:
            raise NotFoundException(ERR_LINK_NOT_FOUND)

        await event_publisher.link_deleted(map_id, result, user_id=request.user.id)
        return result

    # Signature management

    @get("/{map_id:uuid}/nodes/{node_id:uuid}/signatures")
    async def get_node_signatures(
        self,
        request: Request,
        map_service: MapService,
        map_id: UUID,
        node_id: UUID,
    ) -> NodeSignaturesResponse:
        """Get all signatures for a specific node."""
        ctx = await map_service.get_character_context(request.user.id)

        has_access = await map_service.can_access_map(
            map_id=map_id,
            user_id=ctx.user_id,
            corporation_id=ctx.corporation_id,
            alliance_id=ctx.alliance_id,
        )
        if not has_access:
            raise NotAuthorizedException(ERR_MAP_NO_ACCESS)

        signatures = await map_service.get_node_signatures(map_id, node_id)
        return NodeSignaturesResponse(node_id=node_id, signatures=signatures)

    @post("/{map_id:uuid}/signatures")
    async def create_signature(
        self,
        request: Request,
        map_service: MapService,
        event_publisher: EventPublisher,
        map_id: UUID,
        data: CreateSignatureRequest,
    ) -> CreateSignatureResponse:
        """Create a new signature on a node. Full data delivered via SSE."""
        ctx = await map_service.get_character_context(request.user.id)

        has_edit_access = await map_service.has_edit_access(
            map_id=map_id,
            user_id=ctx.user_id,
            corporation_id=ctx.corporation_id,
            alliance_id=ctx.alliance_id,
        )
        if not has_edit_access:
            raise NotAuthorizedException(ERR_MAP_NO_EDIT_ACCESS)

        result = await map_service.create_signature(
            node_id=data.node_id,
            map_id=map_id,
            code=data.code,
            group_type=data.group_type,
            subgroup=data.subgroup,
            type_name=data.type,
            link_id=data.link_id,
            wormhole_id=data.wormhole_id,
        )
        await event_publisher.signature_created(map_id, result, user_id=request.user.id)
        return CreateSignatureResponse(signature_id=result.id)

    @patch("/{map_id:uuid}/signatures/{signature_id:uuid}", dto=UpdateSignatureDTO)
    async def update_signature(
        self,
        request: Request,
        map_service: MapService,
        event_publisher: EventPublisher,
        map_id: UUID,
        signature_id: UUID,
        data: DTOData[UpdateSignatureRequest],
    ) -> UpdateSignatureResponse:
        """Update a signature. Full data delivered via SSE."""
        ctx = await map_service.get_character_context(request.user.id)

        has_edit_access = await map_service.has_edit_access(
            map_id=map_id,
            user_id=ctx.user_id,
            corporation_id=ctx.corporation_id,
            alliance_id=ctx.alliance_id,
        )
        if not has_edit_access:
            raise NotAuthorizedException(ERR_MAP_NO_EDIT_ACCESS)

        # Get only the fields that were provided in the request
        updates = data.as_builtins()

        result = await map_service.update_signature(
            map_id=map_id,
            signature_id=signature_id,
            updates=updates,
        )
        if result is None:
            raise NotFoundException(ERR_SIGNATURE_NOT_FOUND)

        await event_publisher.signature_updated(map_id, result, user_id=request.user.id)
        return UpdateSignatureResponse(signature_id=result.id)

    @delete("/{map_id:uuid}/signatures/{signature_id:uuid}", status_code=HTTP_202_ACCEPTED)
    async def delete_signature(
        self,
        request: Request,
        map_service: MapService,
        event_publisher: EventPublisher,
        map_id: UUID,
        signature_id: UUID,
    ) -> DeleteSignatureResponse:
        """Soft-delete a signature from a node."""
        ctx = await map_service.get_character_context(request.user.id)

        has_edit_access = await map_service.has_edit_access(
            map_id=map_id,
            user_id=ctx.user_id,
            corporation_id=ctx.corporation_id,
            alliance_id=ctx.alliance_id,
        )
        if not has_edit_access:
            raise NotAuthorizedException(ERR_MAP_NO_EDIT_ACCESS)

        result = await map_service.delete_signature(map_id, signature_id)
        if result is None:
            raise NotFoundException(ERR_SIGNATURE_NOT_FOUND)

        await event_publisher.signature_deleted(map_id, result, user_id=request.user.id)
        return result

    @post("/{map_id:uuid}/nodes/{node_id:uuid}/signatures/bulk")
    async def bulk_upsert_signatures(
        self,
        request: Request,
        map_service: MapService,
        event_publisher: EventPublisher,
        map_id: UUID,
        node_id: UUID,
        data: BulkCreateSignatureRequest,
        delete_missing: bool = Parameter(default=False, query="delete_missing"),
    ) -> BulkSignatureResponse:
        """Bulk create/update signatures for a node.

        If delete_missing=true, signatures not in the request will be soft-deleted.
        This is useful for paste-from-clipboard sync operations.
        """
        ctx = await map_service.get_character_context(request.user.id)

        has_edit_access = await map_service.has_edit_access(
            map_id=map_id,
            user_id=ctx.user_id,
            corporation_id=ctx.corporation_id,
            alliance_id=ctx.alliance_id,
        )
        if not has_edit_access:
            raise NotAuthorizedException(ERR_MAP_NO_EDIT_ACCESS)

        # Convert dataclass list to dict list for service
        sig_dicts = [
            {
                "code": s.code,
                "group_type": s.group_type,
                "subgroup": s.subgroup,
                "type": s.type,
                "link_id": s.link_id,
            }
            for s in data.signatures
        ]

        created_ids, updated_ids, deleted_ids = await map_service.bulk_upsert_signatures(
            node_id=node_id,
            map_id=map_id,
            signatures=sig_dicts,
            delete_missing=delete_missing,
        )

        await event_publisher.signatures_bulk_updated(
            map_id, node_id, created_ids, updated_ids, deleted_ids, user_id=request.user.id
        )

        return BulkSignatureResponse(
            created=created_ids,
            updated=updated_ids,
            deleted=deleted_ids,
        )

    # Node connections

    @get("/{map_id:uuid}/nodes/{node_id:uuid}/connections")
    async def get_node_connections(
        self,
        request: Request,
        map_service: MapService,
        map_id: UUID,
        node_id: UUID,
    ) -> NodeConnectionsResponse:
        """Get all connections (links) for a specific node with system names."""
        ctx = await map_service.get_character_context(request.user.id)

        has_access = await map_service.can_access_map(
            map_id=map_id,
            user_id=ctx.user_id,
            corporation_id=ctx.corporation_id,
            alliance_id=ctx.alliance_id,
        )
        if not has_access:
            raise NotAuthorizedException(ERR_MAP_NO_ACCESS)

        connections = await map_service.get_node_connections(map_id, node_id)
        return NodeConnectionsResponse(node_id=node_id, connections=connections)

    @patch("/{map_id:uuid}/links/{link_id:uuid}/set-type")
    async def set_link_type(
        self,
        request: Request,
        map_service: MapService,
        event_publisher: EventPublisher,
        map_id: UUID,
        link_id: UUID,
        data: SetLinkTypeRequest,
    ) -> UpdateLinkResponse:
        """Set wormhole type on a link from a specific node.

        If from_node_id is the target of the link, the link direction will be
        flipped so that from_node_id becomes the source. This ensures the wormhole
        type always represents "outgoing from source".
        """
        ctx = await map_service.get_character_context(request.user.id)

        has_edit_access = await map_service.has_edit_access(
            map_id=map_id,
            user_id=ctx.user_id,
            corporation_id=ctx.corporation_id,
            alliance_id=ctx.alliance_id,
        )
        if not has_edit_access:
            raise NotAuthorizedException(ERR_MAP_NO_EDIT_ACCESS)

        result = await map_service.set_link_type_from_node(
            map_id=map_id,
            link_id=link_id,
            wormhole_id=data.wormhole_id,
            from_node_id=data.from_node_id,
        )
        if result is None:
            raise NotFoundException(ERR_LINK_NODE_MISMATCH)

        await event_publisher.link_updated(map_id, result, user_id=request.user.id)
        return UpdateLinkResponse(link_id=result.id)

    @post("/{map_id:uuid}/signatures/{signature_id:uuid}/connect")
    async def create_connection_from_signature(
        self,
        request: Request,
        map_service: MapService,
        event_publisher: EventPublisher,
        map_id: UUID,
        signature_id: UUID,
        data: CreateConnectionFromSignatureRequest,
    ) -> CreateConnectionFromSignatureResponse:
        """Create a new node + connection from a wormhole signature.

        Creates a destination node at the specified position, creates a link from
        the signature's node to the new node, and associates the signature with
        the new link.
        """
        ctx = await map_service.get_character_context(request.user.id)

        has_edit_access = await map_service.has_edit_access(
            map_id=map_id,
            user_id=ctx.user_id,
            corporation_id=ctx.corporation_id,
            alliance_id=ctx.alliance_id,
        )
        if not has_edit_access:
            raise NotAuthorizedException(ERR_MAP_NO_EDIT_ACCESS)

        result = await map_service.create_connection_from_signature(
            map_id=map_id,
            signature_id=signature_id,
            system_id=data.system_id,
            pos_x=data.pos_x,
            pos_y=data.pos_y,
            wormhole_id=data.wormhole_id,
        )
        if result is None:
            raise NotFoundException(ERR_SIGNATURE_NOT_FOUND)

        # Publish events for the new node, link, and updated signature
        node_source = await map_service.db_session.select_one(
            GET_NODE_ENRICHED,
            result.node_id,
            schema_type=EnrichedNodeSourceData,
        )
        enriched_node = EnrichedNodeInfo.from_source(node_source)
        await event_publisher.node_created(map_id, enriched_node, user_id=request.user.id)

        enriched_link = await map_service.db_session.select_one(
            GET_LINK_ENRICHED,
            result.link_id,
            schema_type=EnrichedLinkInfo,
        )
        await event_publisher.link_created(map_id, enriched_link, user_id=request.user.id)

        enriched_sig = await map_service.db_session.select_one(
            GET_SIGNATURE_ENRICHED,
            result.signature_id,
            schema_type=EnrichedSignatureInfo,
        )
        await event_publisher.signature_updated(map_id, enriched_sig, user_id=request.user.id)

        return result

    # Note management

    @get("/{map_id:uuid}/systems/{system_id:int}/notes")
    async def get_system_notes(
        self,
        request: Request,
        map_service: MapService,
        map_id: UUID,
        system_id: int,
    ) -> SystemNotesResponse:
        """Get all notes for a specific solar system on a map."""
        ctx = await map_service.get_character_context(request.user.id)

        has_access = await map_service.can_access_map(
            map_id=map_id,
            user_id=ctx.user_id,
            corporation_id=ctx.corporation_id,
            alliance_id=ctx.alliance_id,
        )
        if not has_access:
            raise NotAuthorizedException(ERR_MAP_NO_ACCESS)

        notes = await map_service.get_system_notes(map_id, system_id)
        return SystemNotesResponse(solar_system_id=system_id, notes=notes)

    @post("/{map_id:uuid}/notes")
    async def create_note(
        self,
        request: Request,
        map_service: MapService,
        event_publisher: EventPublisher,
        map_id: UUID,
        data: CreateNoteRequest,
    ) -> CreateNoteResponse:
        """Create a new note on a solar system. Full data delivered via SSE."""
        ctx = await map_service.get_character_context(request.user.id)

        has_edit_access = await map_service.has_edit_access(
            map_id=map_id,
            user_id=ctx.user_id,
            corporation_id=ctx.corporation_id,
            alliance_id=ctx.alliance_id,
        )
        if not has_edit_access:
            raise NotAuthorizedException(ERR_MAP_NO_EDIT_ACCESS)

        # Get primary character ID for created_by
        primary_character_id = ctx.primary_character_id
        if primary_character_id is None:
            raise ClientException("No primary character set")

        result = await map_service.create_note(
            solar_system_id=data.solar_system_id,
            map_id=map_id,
            content=data.content,
            created_by=primary_character_id,
            title=data.title,
            date_expires=data.date_expires,
        )
        await event_publisher.note_created(map_id, result, user_id=request.user.id)
        return CreateNoteResponse(note_id=result.id)

    @patch("/{map_id:uuid}/notes/{note_id:uuid}", dto=UpdateNoteDTO)
    async def update_note(
        self,
        request: Request,
        map_service: MapService,
        event_publisher: EventPublisher,
        map_id: UUID,
        note_id: UUID,
        data: DTOData[UpdateNoteRequest],
    ) -> UpdateNoteResponse:
        """Update a note. Full data delivered via SSE."""
        ctx = await map_service.get_character_context(request.user.id)

        has_edit_access = await map_service.has_edit_access(
            map_id=map_id,
            user_id=ctx.user_id,
            corporation_id=ctx.corporation_id,
            alliance_id=ctx.alliance_id,
        )
        if not has_edit_access:
            raise NotAuthorizedException(ERR_MAP_NO_EDIT_ACCESS)

        # Get primary character ID for updated_by
        primary_character_id = ctx.primary_character_id
        if primary_character_id is None:
            raise ClientException("No primary character set")

        # Get only the fields that were provided in the request
        updates = data.as_builtins()

        result = await map_service.update_note(
            map_id=map_id,
            note_id=note_id,
            updated_by=primary_character_id,
            updates=updates,
        )
        if result is None:
            raise NotFoundException(ERR_NOTE_NOT_FOUND)

        await event_publisher.note_updated(map_id, result, user_id=request.user.id)
        return UpdateNoteResponse(note_id=result.id)

    @delete("/{map_id:uuid}/notes/{note_id:uuid}", status_code=HTTP_202_ACCEPTED)
    async def delete_note(
        self,
        request: Request,
        map_service: MapService,
        event_publisher: EventPublisher,
        map_id: UUID,
        note_id: UUID,
    ) -> DeleteNoteResponse:
        """Soft-delete a note from a node."""
        ctx = await map_service.get_character_context(request.user.id)

        has_edit_access = await map_service.has_edit_access(
            map_id=map_id,
            user_id=ctx.user_id,
            corporation_id=ctx.corporation_id,
            alliance_id=ctx.alliance_id,
        )
        if not has_edit_access:
            raise NotAuthorizedException(ERR_MAP_NO_EDIT_ACCESS)

        result = await map_service.delete_note(map_id, note_id)
        if result is None:
            raise NotFoundException(ERR_NOTE_NOT_FOUND)

        await event_publisher.note_deleted(map_id, result, user_id=request.user.id)
        return result
