from __future__ import annotations

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

import msgspec
from litestar.response import ServerSentEvent
from litestar.response.sse import ServerSentEventMessage
from sqlspec import AsyncDriverAdapterBase, sql

from database.models.map import INSERT_STMT as MAP_INSERT
from database.models.map_alliance import DELETE_STMT as MAP_ALLIANCE_DELETE
from database.models.map_alliance import INSERT_STMT as MAP_ALLIANCE_INSERT
from database.models.map_character import DELETE_STMT as MAP_CHARACTER_DELETE
from database.models.map_character import INSERT_STMT as MAP_CHARACTER_INSERT
from database.models.map_corporation import DELETE_STMT as MAP_CORPORATION_DELETE
from database.models.map_corporation import INSERT_STMT as MAP_CORPORATION_INSERT
from services.route_base import CharacterContext, RouteBaseService

from .dependencies import (
    AllianceAccessInfo,
    CharacterAccessInfo,
    CorporationAccessInfo,
    CreateConnectionFromSignatureResponse,
    DeleteLinkResponse,
    DeleteMapResponse,
    DeleteNodeResponse,
    DeleteNoteResponse,
    DeleteSignatureResponse,
    EnrichedLinkInfo,
    EnrichedNodeInfo,
    EnrichedNodeSourceData,
    EnrichedNoteInfo,
    EnrichedSignatureInfo,
    MapAccessResponse,
    MapInfo,
    NodeConnectionInfo,
    PublicMapInfo,
    SignatureUpsertResult,
    SubscriptionResponse,
)
from .events import ACCESS_REVOCATION_TYPES, EventType, MapEvent
from .queries import (
    CHECK_MAP_PUBLIC,
    COUNT_PUBLIC_MAPS,
    COUNT_SEARCH_PUBLIC_MAPS,
    DELETE_LINK,
    DELETE_NODE,
    DELETE_NOTE,
    DELETE_SIGNATURE,
    DELETE_SIGNATURES_NOT_IN_CODES,
    DELETE_SUBSCRIPTION,
    FLIP_LINK_DIRECTION,
    GET_K162_ID,
    GET_LINK_ENRICHED,
    GET_LINK_NODES,
    GET_MAP,
    GET_MAP_LINK_IDS,
    GET_MAP_LINKS,
    GET_MAP_NODE_IDS,
    GET_MAP_NODES,
    GET_MAP_SIGNATURES,
    GET_NODE_CONNECTIONS,
    GET_NODE_ENRICHED,
    GET_NODE_LOCKED,
    GET_NODE_SIGNATURES,
    GET_NOTE_ENRICHED,
    GET_SIGNATURE_ENRICHED,
    GET_SIGNATURE_NODE,
    GET_SUBSCRIPTION_COUNT,
    GET_SYSTEM_NOTES,
    INSERT_LINK,
    INSERT_NODE,
    INSERT_NOTE,
    INSERT_SIGNATURE,
    INSERT_SUBSCRIPTION,
    LIST_ALLIANCE_MAPS,
    LIST_CHARACTER_SHARED_MAPS,
    LIST_CORPORATION_MAPS,
    LIST_MAP_ALLIANCES,
    LIST_MAP_CHARACTERS,
    LIST_MAP_CORPORATIONS,
    LIST_OWNED_MAPS,
    LIST_PUBLIC_MAPS,
    LIST_SUBSCRIBED_MAPS,
    REVERSE_LINK,
    SEARCH_PUBLIC_MAPS,
    SOFT_DELETE_MAP,
    SOFT_DELETE_MAP_LINKS,
    SOFT_DELETE_MAP_NODES,
    SOFT_DELETE_NODE_CONNECTED_LINKS,
    SOFT_DELETE_NODE_SIGNATURES,
    UPDATE_LINK,
    UPDATE_MAP,
    UPDATE_NODE_LOCKED,
    UPDATE_NODE_POSITION,
    UPDATE_NODE_SYSTEM,
    UPDATE_NOTE,
    UPDATE_SIGNATURE_LINK,
    UPSERT_SIGNATURE,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from litestar.channels import ChannelsPlugin
    from valkey.asyncio import Valkey

# Reason codes for sync errors
SYNC_ERROR_INVALID_EVENT_ID = "invalid_event_id"

# SSE response headers
SSE_HEADERS = {"X-Accel-Buffering": "no", "Cache-Control": "no-cache"}


class NodeLockedError(Exception):
    """Raised when attempting to modify a locked node."""

    pass


class MapService(RouteBaseService):
    """Map management business logic."""

    _k162_id: int | None = None  # Class-level cache for K162 wormhole ID

    async def create_map(
        self,
        owner_id: UUID,
        name: str,
        description: str | None = None,
        is_public: bool = False,
        public_read_only: bool = True,
        edge_type: str = "default",
        rankdir: str = "TB",
        auto_layout: bool = False,
        node_sep: int = 50,
        rank_sep: int = 50,
    ) -> MapInfo:
        """Create a new map owned by the given user."""
        return await self.db_session.select_one(
            MAP_INSERT,
            owner_id,
            name,
            description,
            is_public,
            public_read_only,
            edge_type,
            rankdir,
            auto_layout,
            node_sep,
            rank_sep,
            schema_type=MapInfo,
        )

    async def list_owned_maps(self, user_id: UUID) -> list[MapInfo]:
        """List maps owned by the given user."""
        return await self.db_session.select(
            LIST_OWNED_MAPS,
            user_id,
            schema_type=MapInfo,
        )

    async def list_shared_maps(self, user_id: UUID) -> list[MapInfo]:
        """List maps shared with the user via map_character."""
        return await self.db_session.select(
            LIST_CHARACTER_SHARED_MAPS,
            user_id,
            schema_type=MapInfo,
        )

    async def list_corporation_maps(self, corporation_id: int, user_id: UUID) -> list[MapInfo]:
        """List maps shared with the corporation."""
        return await self.db_session.select(
            LIST_CORPORATION_MAPS,
            corporation_id,
            user_id,
            schema_type=MapInfo,
        )

    async def list_alliance_maps(self, alliance_id: int, user_id: UUID, corporation_id: int | None) -> list[MapInfo]:
        """List maps shared with the alliance."""
        return await self.db_session.select(
            LIST_ALLIANCE_MAPS,
            alliance_id,
            user_id,
            corporation_id,
            schema_type=MapInfo,
        )

    async def get_map(self, map_id: UUID) -> MapInfo | None:
        """Get a map by ID."""
        return await self.db_session.select_one_or_none(
            GET_MAP,
            map_id,
            schema_type=MapInfo,
        )

    async def get_map_nodes(self, map_id: UUID) -> list[EnrichedNodeInfo]:
        """Get all enriched nodes for a map."""
        source_nodes = await self.db_session.select(
            GET_MAP_NODES,
            map_id,
            schema_type=EnrichedNodeSourceData,
        )
        return [EnrichedNodeInfo.from_source(node) for node in source_nodes]

    async def get_map_links(self, map_id: UUID) -> list[EnrichedLinkInfo]:
        """Get all enriched links for a map."""
        return await self.db_session.select(
            GET_MAP_LINKS,
            map_id,
            schema_type=EnrichedLinkInfo,
        )

    async def update_map(
        self,
        map_id: UUID,
        name: str | None = None,
        description: str | None = None,
        is_public: bool | None = None,
        public_read_only: bool | None = None,
        edge_type: str | None = None,
        rankdir: str | None = None,
        auto_layout: bool | None = None,
        node_sep: int | None = None,
        rank_sep: int | None = None,
    ) -> MapInfo | None:
        """Update a map. Returns None if map doesn't exist."""
        return await self.db_session.select_one_or_none(
            UPDATE_MAP,
            map_id,
            name,
            description,
            is_public,
            public_read_only,
            edge_type,
            rankdir,
            auto_layout,
            node_sep,
            rank_sep,
            schema_type=MapInfo,
        )

    async def delete_map(self, map_id: UUID) -> DeleteMapResponse | None:
        """Soft-delete a map and all its nodes/links.

        Returns DeleteMapResponse with all deleted IDs, or None if map not found.
        """
        # Get node and link IDs before deletion
        node_ids = [row["id"] for row in await self.db_session.select(GET_MAP_NODE_IDS, map_id)]
        link_ids = [row["id"] for row in await self.db_session.select(GET_MAP_LINK_IDS, map_id)]

        # Soft-delete links first, then nodes, then the map
        await self.db_session.execute(SOFT_DELETE_MAP_LINKS, map_id)
        await self.db_session.execute(SOFT_DELETE_MAP_NODES, map_id)
        result = await self.db_session.select_value(SOFT_DELETE_MAP, map_id)

        if result is None:
            return None

        return DeleteMapResponse(
            map_id=map_id,
            deleted_node_ids=node_ids,
            deleted_link_ids=link_ids,
        )

    async def is_owner(self, map_id: UUID, user_id: UUID) -> bool:
        """Check if user is the owner of the map."""
        map_info = await self.get_map(map_id)
        return map_info is not None and map_info.owner_id == user_id

    async def get_map_access(self, map_id: UUID) -> MapAccessResponse:
        """Get all access entries for a map."""
        characters = await self.db_session.select(
            LIST_MAP_CHARACTERS,
            map_id,
            schema_type=CharacterAccessInfo,
        )
        corporations = await self.db_session.select(
            LIST_MAP_CORPORATIONS,
            map_id,
            schema_type=CorporationAccessInfo,
        )
        alliances = await self.db_session.select(
            LIST_MAP_ALLIANCES,
            map_id,
            schema_type=AllianceAccessInfo,
        )
        return MapAccessResponse(
            characters=characters,
            corporations=corporations,
            alliances=alliances,
        )

    # Character access management

    async def add_character_access(
        self,
        map_id: UUID,
        character_id: int,
        read_only: bool = True,
    ) -> None:
        """Add or update character access to a map."""
        await self.db_session.execute(MAP_CHARACTER_INSERT, map_id, character_id, read_only)

    async def remove_character_access(self, map_id: UUID, character_id: int) -> bool:
        """Remove character access from a map. Returns True if removed."""
        result = await self.db_session.execute(MAP_CHARACTER_DELETE, map_id, character_id)
        return result.num_rows > 0

    # Corporation access management

    async def add_corporation_access(
        self,
        map_id: UUID,
        corporation_id: int,
        read_only: bool = True,
    ) -> None:
        """Add or update corporation access to a map."""
        await self.db_session.execute(MAP_CORPORATION_INSERT, map_id, corporation_id, read_only)

    async def remove_corporation_access(self, map_id: UUID, corporation_id: int) -> bool:
        """Remove corporation access from a map. Returns True if removed."""
        result = await self.db_session.execute(MAP_CORPORATION_DELETE, map_id, corporation_id)
        return result.num_rows > 0

    # Alliance access management

    async def add_alliance_access(
        self,
        map_id: UUID,
        alliance_id: int,
        read_only: bool = True,
    ) -> None:
        """Add or update alliance access to a map."""
        await self.db_session.execute(MAP_ALLIANCE_INSERT, map_id, alliance_id, read_only)

    async def remove_alliance_access(self, map_id: UUID, alliance_id: int) -> bool:
        """Remove alliance access from a map. Returns True if removed."""
        result = await self.db_session.execute(MAP_ALLIANCE_DELETE, map_id, alliance_id)
        return result.num_rows > 0

    # Public map subscription management

    async def list_public_maps(
        self,
        user_id: UUID,
        corporation_id: int | None,
        alliance_id: int | None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[PublicMapInfo], int]:
        """List public maps ordered by popularity (subscription count).

        Excludes maps the user already has access to via ownership, subscription, or explicit shares.
        """
        maps = await self.db_session.select(
            LIST_PUBLIC_MAPS,
            user_id,
            corporation_id,
            alliance_id,
            limit,
            offset,
            schema_type=PublicMapInfo,
        )
        total = await self.db_session.select_value(COUNT_PUBLIC_MAPS, user_id, corporation_id, alliance_id)
        return maps, total or 0

    async def search_public_maps(
        self,
        user_id: UUID,
        corporation_id: int | None,
        alliance_id: int | None,
        query: str,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[PublicMapInfo], int]:
        """Search public maps by name/description.

        Excludes maps the user already has access to via ownership, subscription, or explicit shares.
        """
        maps = await self.db_session.select(
            SEARCH_PUBLIC_MAPS,
            user_id,
            corporation_id,
            alliance_id,
            query,
            limit,
            offset,
            schema_type=PublicMapInfo,
        )
        total = await self.db_session.select_value(
            COUNT_SEARCH_PUBLIC_MAPS, user_id, corporation_id, alliance_id, query
        )
        return maps, total or 0

    async def list_subscribed_maps(self, user_id: UUID) -> list[MapInfo]:
        """List maps the user has subscribed to."""
        return await self.db_session.select(
            LIST_SUBSCRIBED_MAPS,
            user_id,
            schema_type=MapInfo,
        )

    async def subscribe_to_map(self, map_id: UUID, user_id: UUID) -> SubscriptionResponse:
        """Subscribe to a public map.

        Raises ValueError if map doesn't exist or is not public.
        """
        is_public = await self.db_session.select_value(CHECK_MAP_PUBLIC, map_id)
        if is_public is None:
            msg = "Map not found"
            raise ValueError(msg)
        if not is_public:
            msg = "Map is not public"
            raise ValueError(msg)

        await self.db_session.execute(INSERT_SUBSCRIPTION, map_id, user_id)
        count = await self.db_session.select_value(GET_SUBSCRIPTION_COUNT, map_id)

        return SubscriptionResponse(
            map_id=map_id,
            subscribed=True,
            subscription_count=count or 0,
        )

    async def unsubscribe_from_map(self, map_id: UUID, user_id: UUID) -> SubscriptionResponse:
        """Unsubscribe from a public map."""
        await self.db_session.execute(DELETE_SUBSCRIPTION, map_id, user_id)
        count = await self.db_session.select_value(GET_SUBSCRIPTION_COUNT, map_id)

        return SubscriptionResponse(
            map_id=map_id,
            subscribed=False,
            subscription_count=count or 0,
        )

    # Node management

    async def is_node_locked(self, node_id: UUID, map_id: UUID) -> bool | None:
        """Check if a node is locked. Returns None if node doesn't exist or doesn't belong to map."""
        return await self.db_session.select_value(GET_NODE_LOCKED, node_id, map_id)

    async def update_node_locked(
        self,
        map_id: UUID,
        node_id: UUID,
        locked: bool,
    ) -> EnrichedNodeInfo | None:
        """Update a node's locked status. Returns None if node doesn't exist or doesn't belong to map."""
        result = await self.db_session.execute(UPDATE_NODE_LOCKED, node_id, locked, map_id)
        if result.num_rows == 0:
            return None

        source = await self.db_session.select_one(
            GET_NODE_ENRICHED,
            node_id,
            schema_type=EnrichedNodeSourceData,
        )
        return EnrichedNodeInfo.from_source(source)

    async def create_node(
        self,
        map_id: UUID,
        system_id: int,
        pos_x: float,
        pos_y: float,
    ) -> EnrichedNodeInfo:
        """Create a new node on the map."""
        node_id = await self.db_session.select_value(
            INSERT_NODE,
            map_id,
            system_id,
            pos_x,
            pos_y,
        )
        source = await self.db_session.select_one(
            GET_NODE_ENRICHED,
            node_id,
            schema_type=EnrichedNodeSourceData,
        )
        return EnrichedNodeInfo.from_source(source)

    async def update_node_position(
        self,
        map_id: UUID,
        node_id: UUID,
        pos_x: float,
        pos_y: float,
    ) -> EnrichedNodeInfo | None:
        """Update a node's position. Returns None if node doesn't exist or doesn't belong to map."""
        # Check if node is locked
        is_locked = await self.is_node_locked(node_id, map_id)
        if is_locked is None:
            return None  # Node doesn't exist or doesn't belong to map
        if is_locked:
            raise NodeLockedError("Node is locked")

        result = await self.db_session.execute(UPDATE_NODE_POSITION, node_id, pos_x, pos_y, map_id)
        if result.num_rows == 0:
            return None

        source = await self.db_session.select_one(
            GET_NODE_ENRICHED,
            node_id,
            schema_type=EnrichedNodeSourceData,
        )
        return EnrichedNodeInfo.from_source(source)

    async def update_node_system(
        self,
        map_id: UUID,
        node_id: UUID,
        system_id: int,
    ) -> EnrichedNodeInfo | None:
        """Update a node's system. Returns None if node doesn't exist or doesn't belong to map."""
        # Check if node is locked
        is_locked = await self.is_node_locked(node_id, map_id)
        if is_locked is None:
            return None  # Node doesn't exist or doesn't belong to map
        if is_locked:
            raise NodeLockedError("Node is locked")

        result = await self.db_session.execute(UPDATE_NODE_SYSTEM, node_id, system_id, map_id)
        if result.num_rows == 0:
            return None

        source = await self.db_session.select_one(
            GET_NODE_ENRICHED,
            node_id,
            schema_type=EnrichedNodeSourceData,
        )
        return EnrichedNodeInfo.from_source(source)

    async def delete_node(
        self,
        map_id: UUID,
        node_id: UUID,
    ) -> DeleteNodeResponse | None:
        """Soft-delete a node and its connected links and signatures.

        Returns DeleteNodeResponse with deleted link and signature IDs, or None if node not found
        or doesn't belong to the specified map.
        """
        # Soft-delete connected links first, collecting their IDs
        deleted_link_rows = await self.db_session.select(SOFT_DELETE_NODE_CONNECTED_LINKS, node_id, map_id)
        deleted_link_ids = [row["id"] for row in deleted_link_rows]

        # Soft-delete signatures for this node
        deleted_sig_rows = await self.db_session.select(SOFT_DELETE_NODE_SIGNATURES, node_id, map_id)
        deleted_signature_ids = [row["id"] for row in deleted_sig_rows]

        # Soft-delete the node
        result = await self.db_session.execute(DELETE_NODE, node_id, map_id)
        if result.num_rows == 0:
            return None

        return DeleteNodeResponse(
            node_id=node_id,
            deleted_link_ids=deleted_link_ids,
            deleted_signature_ids=deleted_signature_ids,
        )

    # Link management

    async def get_k162_id(self) -> int | None:
        """Get the ID of the K162 wormhole type (cached after first lookup)."""
        if MapService._k162_id is None:
            MapService._k162_id = await self.db_session.select_value(GET_K162_ID)
        return MapService._k162_id

    async def create_link(
        self,
        map_id: UUID,
        source_node_id: UUID,
        target_node_id: UUID,
        wormhole_id: int | None = None,
    ) -> EnrichedLinkInfo:
        """Create a new link between nodes. Defaults to K162 if no wormhole specified."""
        if wormhole_id is None:
            wormhole_id = await self.get_k162_id()

        link_id = await self.db_session.select_value(
            INSERT_LINK,
            map_id,
            source_node_id,
            target_node_id,
            wormhole_id,
        )
        return await self.db_session.select_one(
            GET_LINK_ENRICHED,
            link_id,
            schema_type=EnrichedLinkInfo,
        )

    async def update_link(
        self,
        map_id: UUID,
        link_id: UUID,
        wormhole_id: int | None = None,
        lifetime_status: str | None = None,
        mass_usage: int | None = None,
        reverse: bool | None = None,
    ) -> EnrichedLinkInfo | None:
        """Update a link. Returns None if link doesn't exist or doesn't belong to map."""
        # Handle reverse if requested
        if reverse is True:
            await self.db_session.execute(REVERSE_LINK, link_id, map_id)

        result = await self.db_session.execute(
            UPDATE_LINK,
            link_id,
            wormhole_id,
            lifetime_status,
            mass_usage,
            map_id,
        )
        if result.num_rows == 0:
            return None

        return await self.db_session.select_one(
            GET_LINK_ENRICHED,
            link_id,
            schema_type=EnrichedLinkInfo,
        )

    async def delete_link(
        self,
        map_id: UUID,
        link_id: UUID,
    ) -> DeleteLinkResponse | None:
        """Soft-delete a link. Returns None if link doesn't exist or doesn't belong to map."""
        result = await self.db_session.execute(DELETE_LINK, link_id, map_id)
        if result.num_rows == 0:
            return None

        return DeleteLinkResponse(link_id=link_id)

    # Signature management

    async def get_map_signatures(self, map_id: UUID) -> list[EnrichedSignatureInfo]:
        """Get all signatures for a map."""
        return await self.db_session.select(
            GET_MAP_SIGNATURES,
            map_id,
            schema_type=EnrichedSignatureInfo,
        )

    async def get_node_signatures(self, map_id: UUID, node_id: UUID) -> list[EnrichedSignatureInfo]:
        """Get all signatures for a specific node. Only returns signatures if node belongs to map."""
        return await self.db_session.select(
            GET_NODE_SIGNATURES,
            node_id,
            map_id,
            schema_type=EnrichedSignatureInfo,
        )

    async def create_signature(
        self,
        node_id: UUID,
        map_id: UUID,
        code: str,
        group_type: str,
        subgroup: str | None = None,
        type_name: str | None = None,
        link_id: UUID | None = None,
        wormhole_id: int | None = None,
    ) -> EnrichedSignatureInfo:
        """Create a new signature on a node."""
        signature_id = await self.db_session.select_value(
            INSERT_SIGNATURE,
            node_id,
            map_id,
            code.upper(),  # Normalize signature codes to uppercase
            group_type,
            subgroup,
            type_name,
            link_id,
            wormhole_id,
        )
        return await self.db_session.select_one(
            GET_SIGNATURE_ENRICHED,
            signature_id,
            schema_type=EnrichedSignatureInfo,
        )

    async def update_signature(
        self,
        map_id: UUID,
        signature_id: UUID,
        updates: dict,
    ) -> EnrichedSignatureInfo | None:
        """Update a signature with partial updates.

        Args:
            map_id: The map the signature must belong to
            signature_id: The signature to update
            updates: Dict of field names to values. Only provided fields are updated.
                     Supports: code, group_type, subgroup, type, link_id

        Returns None if signature doesn't exist or doesn't belong to map.
        """
        if not updates:
            # No updates, just return current state (with map verification via query)
            return await self.db_session.select_one_or_none(
                GET_SIGNATURE_ENRICHED,
                signature_id,
                schema_type=EnrichedSignatureInfo,
            )

        # Normalize code to uppercase if provided
        if "code" in updates and updates["code"] is not None:
            updates["code"] = updates["code"].upper()

        # Build dynamic update query with map_id check
        query = sql.update("signature").where("id = :id AND map_id = :map_id AND date_deleted IS NULL")
        for field, value in updates.items():
            query = query.set(field, value)

        result = await self.db_session.execute(query, {"id": signature_id, "map_id": map_id, **updates})
        if result.num_rows == 0:
            return None

        return await self.db_session.select_one(
            GET_SIGNATURE_ENRICHED,
            signature_id,
            schema_type=EnrichedSignatureInfo,
        )

    async def delete_signature(
        self,
        map_id: UUID,
        signature_id: UUID,
    ) -> DeleteSignatureResponse | None:
        """Soft-delete a signature. Returns None if signature doesn't exist or doesn't belong to map."""
        result = await self.db_session.execute(DELETE_SIGNATURE, signature_id, map_id)
        if result.num_rows == 0:
            return None

        return DeleteSignatureResponse(signature_id=signature_id)

    async def _delete_missing_signatures(self, node_id: UUID, codes: list[str]) -> list[UUID]:
        """Delete signatures not in the provided codes list."""
        deleted_rows = await self.db_session.select(
            DELETE_SIGNATURES_NOT_IN_CODES,
            node_id,
            codes,
        )
        return [row["id"] for row in deleted_rows]

    async def _upsert_signature(
        self,
        node_id: UUID,
        map_id: UUID,
        code: str,
        group_type: str,
        subgroup: str | None,
        sig_type: str | None,
    ) -> SignatureUpsertResult:
        """Execute a single signature upsert and return the result row."""

        result = await self.db_session.execute(
            UPSERT_SIGNATURE,
            node_id,
            map_id,
            code,
            group_type,
            subgroup,
            sig_type,
        )
        return result.one(schema_type=SignatureUpsertResult)

    async def bulk_upsert_signatures(
        self,
        node_id: UUID,
        map_id: UUID,
        signatures: list[dict],
        delete_missing: bool = False,
    ) -> tuple[list[UUID], list[UUID], list[UUID]]:
        """Bulk upsert signatures for a node.

        Returns (created_ids, updated_ids, deleted_ids) tuples of UUIDs.
        If delete_missing is True, signatures not in the input list will be soft-deleted.
        """
        if not signatures:
            deleted_ids = await self._delete_missing_signatures(node_id, []) if delete_missing else []
            return [], [], deleted_ids

        codes = [s["code"].upper() for s in signatures]

        # Execute upserts and classify by is_insert from RETURNING
        created_ids: list[UUID] = []
        updated_ids: list[UUID] = []

        for s in signatures:
            row = await self._upsert_signature(
                node_id,
                map_id,
                s["code"].upper(),
                s.get("group_type", "signature"),
                s.get("subgroup"),
                s.get("type"),
            )
            if row.is_insert:
                created_ids.append(row.id)
            else:
                updated_ids.append(row.id)

        deleted_ids = await self._delete_missing_signatures(node_id, codes) if delete_missing else []

        return created_ids, updated_ids, deleted_ids

    # Node connection methods

    async def get_node_connections(self, map_id: UUID, node_id: UUID) -> list[NodeConnectionInfo]:
        """Get all connections (links) for a node with system names. Only returns connections if node belongs to map."""
        return await self.db_session.select(
            GET_NODE_CONNECTIONS,
            node_id,
            map_id,
            schema_type=NodeConnectionInfo,
        )

    async def set_link_type_from_node(
        self,
        map_id: UUID,
        link_id: UUID,
        wormhole_id: int,
        from_node_id: UUID,
    ) -> EnrichedLinkInfo | None:
        """Set wormhole type on a link, flipping direction if needed.

        If from_node_id is the target of the link, we flip source/target
        so that the wormhole type always represents "outgoing from source".

        Returns None if link doesn't exist or doesn't belong to map.
        """
        # Get current link state (with map_id verification)
        link_row = await self.db_session.select_one_or_none(GET_LINK_NODES, link_id, map_id)
        if link_row is None:
            return None

        source_node_id = link_row["source_node_id"]
        target_node_id = link_row["target_node_id"]

        if from_node_id == target_node_id:
            # User is setting type from target side - flip the link
            await self.db_session.execute(FLIP_LINK_DIRECTION, link_id, wormhole_id, map_id)
        elif from_node_id == source_node_id:
            # User is setting type from source side - just update
            await self.db_session.execute(UPDATE_LINK, link_id, wormhole_id, None, None, map_id)
        else:
            # from_node_id doesn't match either end - invalid
            return None

        return await self.db_session.select_one(
            GET_LINK_ENRICHED,
            link_id,
            schema_type=EnrichedLinkInfo,
        )

    async def create_connection_from_signature(
        self,
        map_id: UUID,
        signature_id: UUID,
        system_id: int,
        pos_x: float,
        pos_y: float,
        wormhole_id: int | None = None,
    ) -> CreateConnectionFromSignatureResponse | None:
        """Create a new node + connection from a wormhole signature.

        1. Get signature's node_id (becomes link source) - verifies signature belongs to map
        2. Create destination node
        3. Create link with wormhole type
        4. Associate signature with link

        Returns None if signature doesn't exist or doesn't belong to the specified map.
        """
        # Get signature info (with map_id verification)
        sig_row = await self.db_session.select_one_or_none(GET_SIGNATURE_NODE, signature_id, map_id)
        if sig_row is None:
            return None

        source_node_id = sig_row["node_id"]

        # Default to K162 if no wormhole type specified
        if wormhole_id is None:
            wormhole_id = await self.get_k162_id()

        # Create destination node
        new_node_id = await self.db_session.select_value(
            INSERT_NODE,
            map_id,
            system_id,
            pos_x,
            pos_y,
        )

        # Create link
        new_link_id = await self.db_session.select_value(
            INSERT_LINK,
            map_id,
            source_node_id,
            new_node_id,
            wormhole_id,
        )

        # Associate signature with link
        await self.db_session.execute(UPDATE_SIGNATURE_LINK, signature_id, new_link_id, map_id)

        return CreateConnectionFromSignatureResponse(
            node_id=new_node_id,
            link_id=new_link_id,
            signature_id=signature_id,
        )

    # Note management

    async def get_system_notes(self, map_id: UUID, solar_system_id: int) -> list[EnrichedNoteInfo]:
        """Get all notes for a specific solar system on a map."""
        return await self.db_session.select(
            GET_SYSTEM_NOTES,
            solar_system_id,
            map_id,
            schema_type=EnrichedNoteInfo,
        )

    async def create_note(
        self,
        solar_system_id: int,
        map_id: UUID,
        content: str,
        created_by: int,
        title: str | None = None,
        date_expires: datetime | None = None,
    ) -> EnrichedNoteInfo:
        """Create a new note on a solar system within a map."""
        note_id = await self.db_session.select_value(
            INSERT_NOTE,
            solar_system_id,
            map_id,
            title,
            content,
            created_by,
            date_expires,
        )
        return await self.db_session.select_one(
            GET_NOTE_ENRICHED,
            note_id,
            schema_type=EnrichedNoteInfo,
        )

    async def update_note(
        self,
        map_id: UUID,
        note_id: UUID,
        updated_by: int,
        updates: dict,
    ) -> EnrichedNoteInfo | None:
        """Update a note with partial updates.

        Args:
            map_id: The map the note must belong to
            note_id: The note to update
            updated_by: Character ID of the user making the update
            updates: Dict of field names to values. Only provided fields are updated.
                     Supports: title, content, date_expires

        Returns None if note doesn't exist or doesn't belong to map.
        """
        # Extract values from updates dict, using None for missing keys
        title = updates.get("title")
        content = updates.get("content")
        date_expires = updates.get("date_expires")

        result = await self.db_session.execute(
            UPDATE_NOTE,
            note_id,
            title,
            content,
            date_expires,
            updated_by,
            map_id,
        )
        if result.num_rows == 0:
            return None

        return await self.db_session.select_one(
            GET_NOTE_ENRICHED,
            note_id,
            schema_type=EnrichedNoteInfo,
        )

    async def delete_note(
        self,
        map_id: UUID,
        note_id: UUID,
    ) -> DeleteNoteResponse | None:
        """Soft-delete a note. Returns None if note doesn't exist or doesn't belong to map."""
        result = await self.db_session.execute(DELETE_NOTE, note_id, map_id)
        if result.num_rows == 0:
            return None

        return DeleteNoteResponse(note_id=note_id)

    # SSE event subscription

    async def subscribe_events(
        self,
        map_id: UUID,
        ctx: CharacterContext,
        channels: ChannelsPlugin,
        valkey_client: Valkey,
        last_event_id: str | None = None,
    ) -> ServerSentEvent:
        """Subscribe to real-time map events via SSE.

        Returns a ServerSentEvent stream for map changes (nodes, links, map updates).
        History of up to 50 recent events is sent on initial connection.

        Supports resumption via last_event_id - events before the provided ID will be skipped.

        Access revocation events are intercepted and will terminate the stream
        if the user no longer has access to the map.
        """

        channel_name = f"map:{map_id}"

        # Validate last_event_id if provided
        if last_event_id is not None:
            current_seq_bytes = await valkey_client.get(f"map_event_seq:{map_id}")
            current_seq = int(current_seq_bytes.decode()) if current_seq_bytes else 0
            is_valid, requested_id, error_data = self._validate_last_event(last_event_id, current_seq)

            if not is_valid and error_data is not None:
                return ServerSentEvent(
                    self._error_generator(error_data),
                    headers=SSE_HEADERS,
                )

        return ServerSentEvent(
            self._event_generator(ctx, channels, channel_name, last_event_id, map_id),
            headers=SSE_HEADERS,
        )

    # SSE event subscription helpers

    async def _event_generator(
        self,
        ctx: CharacterContext,
        channels: ChannelsPlugin,
        channel_name: str,
        last_event_id: str | None,
        map_id: UUID,
    ) -> AsyncGenerator[ServerSentEventMessage]:
        async with channels.start_subscription([channel_name]) as subscriber:
            # Send history first (up to 50 events)
            await channels.put_subscriber_history(subscriber, [channel_name], limit=50)
            seen_last_event = last_event_id is None  # If no ID, don't skip anything

            # Send connection comment
            yield ServerSentEventMessage(comment="connect")

            # Access the underlying queue directly for timeout support
            queue = subscriber._queue
            while True:
                try:
                    event_data = await asyncio.wait_for(queue.get(), timeout=30.0)
                except TimeoutError:
                    yield ServerSentEventMessage(comment="keepalive")
                    continue

                # None signals subscription shutdown
                if event_data is None:
                    queue.task_done()
                    break

                queue.task_done()
                event = msgspec.json.decode(event_data, type=MapEvent)

                # Filter events based on last_event_id
                should_skip, seen_last_event = self._filter_events(event, last_event_id, seen_last_event)
                if should_skip:
                    continue

                # Check if this is an access revocation that affects this user
                if event.event_type in ACCESS_REVOCATION_TYPES and _revocation_applies_to_user(event, ctx):
                    # Re-verify access before disconnecting
                    still_has_access = await self.can_access_map(
                        map_id=map_id,
                        user_id=ctx.user_id,
                        corporation_id=ctx.corporation_id,
                        alliance_id=ctx.alliance_id,
                    )
                    if not still_has_access:
                        # Send the revocation event, then terminate
                        yield ServerSentEventMessage(
                            data=event_data.decode(),
                            event=event.event_type,
                            id=event.event_id,
                        )
                        return  # Close the SSE stream

                # Normal event - forward to client
                yield ServerSentEventMessage(
                    data=event_data.decode(),
                    event=event.event_type,
                    id=event.event_id,
                )

    @staticmethod
    async def _error_generator(error_data: dict) -> AsyncGenerator[ServerSentEventMessage]:
        yield ServerSentEventMessage(
            data=msgspec.json.encode(error_data).decode(),
            event=EventType.SYNC_ERROR,
        )

    @staticmethod
    def _validate_last_event(
        last_event_id: str,
        current_seq: int,
    ) -> tuple[bool, int | None, dict | None]:
        """Validate the last_event_id against the current sequence.

        Returns:
            A tuple of (is_valid, requested_id, error_data).
            - is_valid: True if valid or non-numeric (pass-through), False if invalid
            - requested_id: The parsed numeric ID if valid, None otherwise
            - error_data: Error details dict if invalid, None otherwise
        """
        try:
            requested_id = int(last_event_id)
            if requested_id > current_seq:
                return (
                    False,
                    requested_id,
                    {
                        "reason": SYNC_ERROR_INVALID_EVENT_ID,
                        "message": "Requested event ID does not exist. Please reload the map.",
                        "requested_id": requested_id,
                        "current_id": current_seq,
                    },
                )
            return True, requested_id, None
        except ValueError:
            # Non-numeric ID, let it through to exact-match logic
            return True, None, None

    @staticmethod
    def _filter_events(
        event: MapEvent,
        last_event_id: str | None,
        seen_last_event: bool,
    ) -> tuple[bool, bool]:
        """Determine if an event should be skipped based on last_event_id.

        Returns:
            A tuple of (should_skip, new_seen_last_event).
            - should_skip: True if this event should be skipped
            - new_seen_last_event: Updated seen_last_event state
        """
        if seen_last_event or last_event_id is None:
            return False, seen_last_event

        try:
            current_id = int(event.event_id)
            target_id = int(last_event_id)
            if current_id <= target_id:
                # Still catching up through history, skip events we already have
                return True, False
            # current_id > target_id: we've passed the client's last event
            return False, True
        except ValueError:
            # Non-numeric event IDs - fall back to exact match
            if event.event_id == last_event_id:
                return True, True
            return True, False


def _revocation_applies_to_user(event: MapEvent, ctx: CharacterContext) -> bool:
    """Check if an access revocation event affects this user."""
    match event.event_type:
        case EventType.ACCESS_CHARACTER_REVOKED:
            return event.data.get("character_id") in ctx.character_ids
        case EventType.ACCESS_CORPORATION_REVOKED:
            return event.data.get("corporation_id") == ctx.corporation_id
        case EventType.ACCESS_ALLIANCE_REVOKED:
            return event.data.get("alliance_id") == ctx.alliance_id
        case _:
            return False


async def provide_map_service(db_session: AsyncDriverAdapterBase) -> MapService:
    """Provide MapService with injected database session."""
    return MapService(db_session)
