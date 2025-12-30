from __future__ import annotations

from uuid import UUID

from sqlspec import AsyncDriverAdapterBase

from database.models.map import INSERT_STMT as MAP_INSERT
from database.models.map_alliance import DELETE_STMT as MAP_ALLIANCE_DELETE
from database.models.map_alliance import INSERT_STMT as MAP_ALLIANCE_INSERT
from database.models.map_corporation import DELETE_STMT as MAP_CORPORATION_DELETE
from database.models.map_corporation import INSERT_STMT as MAP_CORPORATION_INSERT
from database.models.map_user import DELETE_STMT as MAP_USER_DELETE
from database.models.map_user import INSERT_STMT as MAP_USER_INSERT
from routes.maps.dependencies import (
    CharacterContext,
    EnrichedLinkInfo,
    EnrichedNodeInfo,
    MapInfo,
    UserCharacter,
)
from routes.maps.event_queue import MapEventQueue
from routes.maps.events import MapEvent


def _serialize_node_for_event(node: EnrichedNodeInfo) -> dict:
    """Serialize an EnrichedNodeInfo to a dict for event payloads."""
    return {
        "id": str(node.id),
        "pos_x": node.pos_x,
        "pos_y": node.pos_y,
        "system_id": node.system_id,
        "system_name": node.system_name,
        "constellation_id": node.constellation_id,
        "constellation_name": node.constellation_name,
        "region_id": node.region_id,
        "region_name": node.region_name,
        "security_status": node.security_status,
        "security_class": node.security_class,
        "wh_effect_name": node.wh_effect_name,
        "class_name": node.class_name,
        "wh_effect_buffs": node.wh_effect_buffs,
        "wh_effect_debuffs": node.wh_effect_debuffs,
    }


def _serialize_link_for_event(link: EnrichedLinkInfo) -> dict:
    """Serialize an EnrichedLinkInfo to a dict for event payloads."""
    return {
        "id": str(link.id),
        "source_node_id": str(link.source_node_id),
        "target_node_id": str(link.target_node_id),
        "wormhole_code": link.wormhole_code,
        "wormhole_mass_total": link.wormhole_mass_total,
        "wormhole_mass_jump_max": link.wormhole_mass_jump_max,
        "wormhole_mass_regen": link.wormhole_mass_regen,
        "wormhole_lifetime": link.wormhole_lifetime,
        "lifetime_status": link.lifetime_status,
        "date_lifetime_updated": link.date_lifetime_updated.isoformat(),
        "mass_usage": link.mass_usage,
        "date_mass_updated": link.date_mass_updated.isoformat(),
    }
from routes.maps.queries import (
    CHECK_ACCESS,
    CHECK_EDIT_ACCESS,
    DELETE_LINK,
    DELETE_MAP,
    DELETE_NODE,
    GET_K162_ID,
    GET_LINK_ENRICHED,
    GET_LINK_MAP_ID,
    GET_MAP,
    GET_MAP_LINKS,
    GET_MAP_NODES,
    GET_NODE_ENRICHED,
    GET_NODE_MAP_ID,
    GET_USER_CHARACTER,
    INSERT_LINK,
    INSERT_NODE,
    LIST_ALLIANCE_MAPS,
    LIST_CORPORATION_MAPS,
    LIST_OWNED_MAPS,
    LIST_SHARED_MAPS,
    UPDATE_LINK,
    UPDATE_MAP,
    UPDATE_NODE_POSITION,
    UPDATE_NODE_SYSTEM,
)


class MapService:
    """Map management business logic."""

    def __init__(self, db_session: AsyncDriverAdapterBase, event_queue: MapEventQueue | None = None) -> None:
        self.db_session = db_session
        self.event_queue = event_queue

    async def create_map(
        self,
        owner_id: UUID,
        name: str,
        description: str | None = None,
        is_public: bool = False,
    ) -> MapInfo:
        """Create a new map owned by the given user."""
        return await self.db_session.select_one(
            MAP_INSERT,
            owner_id,
            name,
            description,
            is_public,
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
        """List maps shared with the user via map_user."""
        return await self.db_session.select(
            LIST_SHARED_MAPS,
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
        return await self.db_session.select(
            GET_MAP_NODES,
            map_id,
            schema_type=EnrichedNodeInfo,
        )

    async def get_map_links(self, map_id: UUID) -> list[EnrichedLinkInfo]:
        """Get all enriched links for a map."""
        return await self.db_session.select(
            GET_MAP_LINKS,
            map_id,
            schema_type=EnrichedLinkInfo,
        )

    async def can_access_map(
        self,
        map_id: UUID,
        user_id: UUID,
        corporation_id: int | None,
        alliance_id: int | None,
    ) -> bool:
        """Check if user has access to the map."""
        return await self.db_session.select_value(
            CHECK_ACCESS,
            map_id,
            user_id,
            corporation_id,
            alliance_id,
        )

    async def has_edit_access(
        self,
        map_id: UUID,
        user_id: UUID,
        corporation_id: int | None,
        alliance_id: int | None,
    ) -> bool:
        """Check if user has edit access to the map (priority: owner > user > corp > alliance)."""
        result = await self.db_session.select_value(
            CHECK_EDIT_ACCESS,
            map_id,
            user_id,
            corporation_id,
            alliance_id,
        )
        return result or False

    async def get_character_context(self, user_id: UUID) -> CharacterContext:
        """Get the user's character context for access checks."""
        row = await self.db_session.select_one_or_none(GET_USER_CHARACTER, user_id, schema_type=UserCharacter)
        if row is None:
            return CharacterContext(user_id=user_id, corporation_id=None, alliance_id=None)
        return CharacterContext(
            user_id=user_id,
            corporation_id=row.corporation_id,
            alliance_id=row.alliance_id,
        )

    async def update_map(
        self,
        map_id: UUID,
        name: str | None = None,
        description: str | None = None,
        is_public: bool | None = None,
    ) -> MapInfo | None:
        """Update a map. Returns None if map doesn't exist."""
        return await self.db_session.select_one_or_none(
            UPDATE_MAP,
            map_id,
            name,
            description,
            is_public,
            schema_type=MapInfo,
        )

    async def delete_map(self, map_id: UUID) -> bool:
        """Delete a map. Returns True if deleted."""
        result = await self.db_session.execute(DELETE_MAP, map_id)
        return result.num_rows > 0

    async def is_owner(self, map_id: UUID, user_id: UUID) -> bool:
        """Check if user is the owner of the map."""
        map_info = await self.get_map(map_id)
        return map_info is not None and map_info.owner_id == user_id

    # User access management

    async def add_user_access(
        self,
        map_id: UUID,
        user_id: UUID,
        read_only: bool = True,
    ) -> None:
        """Add or update user access to a map."""
        await self.db_session.execute(MAP_USER_INSERT, map_id, user_id, read_only)

    async def remove_user_access(self, map_id: UUID, user_id: UUID) -> bool:
        """Remove user access from a map. Returns True if removed."""
        result = await self.db_session.execute(MAP_USER_DELETE, map_id, user_id)
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

    # Node management

    async def create_node(
        self,
        map_id: UUID,
        system_id: int,
        pos_x: float,
        pos_y: float,
        user_id: UUID | None = None,
    ) -> EnrichedNodeInfo:
        """Create a new node on the map."""
        node_id = await self.db_session.select_value(
            INSERT_NODE,
            map_id,
            system_id,
            pos_x,
            pos_y,
        )
        node = await self.db_session.select_one(
            GET_NODE_ENRICHED,
            node_id,
            schema_type=EnrichedNodeInfo,
        )

        # Publish event with full node data
        if self.event_queue:
            event_id = await self.event_queue.get_next_event_id(map_id)
            event = MapEvent.node_created(
                event_id=event_id,
                map_id=map_id,
                node_data=_serialize_node_for_event(node),
                user_id=user_id,
            )
            await self.event_queue.publish_event(event)

        return node

    async def update_node_position(
        self,
        node_id: UUID,
        pos_x: float,
        pos_y: float,
        user_id: UUID | None = None,
    ) -> EnrichedNodeInfo | None:
        """Update a node's position."""
        # Get the map_id for event publishing
        map_id = await self.db_session.select_value(GET_NODE_MAP_ID, node_id)
        if map_id is None:
            return None

        result = await self.db_session.execute(UPDATE_NODE_POSITION, node_id, pos_x, pos_y)
        if result.num_rows == 0:
            return None

        node = await self.db_session.select_one(
            GET_NODE_ENRICHED,
            node_id,
            schema_type=EnrichedNodeInfo,
        )

        # Publish event with position data only
        if self.event_queue:
            event_id = await self.event_queue.get_next_event_id(map_id)
            event = MapEvent.node_updated(
                event_id=event_id,
                map_id=map_id,
                update_data={
                    "id": str(node_id),
                    "pos_x": pos_x,
                    "pos_y": pos_y,
                },
                user_id=user_id,
            )
            await self.event_queue.publish_event(event)

        return node

    async def update_node_system(
        self,
        node_id: UUID,
        system_id: int,
        user_id: UUID | None = None,
    ) -> EnrichedNodeInfo | None:
        """Update a node's system."""
        # Get the map_id for event publishing
        map_id = await self.db_session.select_value(GET_NODE_MAP_ID, node_id)
        if map_id is None:
            return None

        result = await self.db_session.execute(UPDATE_NODE_SYSTEM, node_id, system_id)
        if result.num_rows == 0:
            return None

        node = await self.db_session.select_one(
            GET_NODE_ENRICHED,
            node_id,
            schema_type=EnrichedNodeInfo,
        )

        # Publish event with full updated node data (system change)
        if self.event_queue:
            event_id = await self.event_queue.get_next_event_id(map_id)
            event = MapEvent.node_updated(
                event_id=event_id,
                map_id=map_id,
                update_data=_serialize_node_for_event(node),
                user_id=user_id,
            )
            await self.event_queue.publish_event(event)

        return node

    async def delete_node(
        self,
        node_id: UUID,
        user_id: UUID | None = None,
    ) -> bool:
        """Delete a node. Returns True if deleted."""
        # Get the map_id for event publishing before deletion
        map_id = await self.db_session.select_value(GET_NODE_MAP_ID, node_id)
        if map_id is None:
            return False

        result = await self.db_session.execute(DELETE_NODE, node_id)
        deleted = result.num_rows > 0

        # Publish event
        if deleted and self.event_queue:
            event_id = await self.event_queue.get_next_event_id(map_id)
            event = MapEvent.node_deleted(
                event_id=event_id,
                map_id=map_id,
                node_id=node_id,
                user_id=user_id,
            )
            await self.event_queue.publish_event(event)

        return deleted

    # Link management

    async def get_k162_id(self) -> int | None:
        """Get the ID of the K162 wormhole type."""
        return await self.db_session.select_value(GET_K162_ID)

    async def create_link(
        self,
        map_id: UUID,
        source_node_id: UUID,
        target_node_id: UUID,
        wormhole_id: int | None = None,
        user_id: UUID | None = None,
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
        link = await self.db_session.select_one(
            GET_LINK_ENRICHED,
            link_id,
            schema_type=EnrichedLinkInfo,
        )

        # Publish event with full link data
        if self.event_queue:
            event_id = await self.event_queue.get_next_event_id(map_id)
            event = MapEvent.link_created(
                event_id=event_id,
                map_id=map_id,
                link_data=_serialize_link_for_event(link),
                user_id=user_id,
            )
            await self.event_queue.publish_event(event)

        return link

    async def update_link(
        self,
        link_id: UUID,
        wormhole_id: int | None = None,
        lifetime_status: str | None = None,
        mass_usage: int | None = None,
        user_id: UUID | None = None,
    ) -> EnrichedLinkInfo | None:
        """Update a link."""
        # Get the map_id for event publishing
        map_id = await self.db_session.select_value(GET_LINK_MAP_ID, link_id)
        if map_id is None:
            return None

        result = await self.db_session.execute(
            UPDATE_LINK,
            link_id,
            wormhole_id,
            lifetime_status,
            mass_usage,
        )
        if result.num_rows == 0:
            return None

        link = await self.db_session.select_one(
            GET_LINK_ENRICHED,
            link_id,
            schema_type=EnrichedLinkInfo,
        )

        # Publish event with full updated link data
        if self.event_queue:
            event_id = await self.event_queue.get_next_event_id(map_id)
            event = MapEvent.link_updated(
                event_id=event_id,
                map_id=map_id,
                link_data=_serialize_link_for_event(link),
                user_id=user_id,
            )
            await self.event_queue.publish_event(event)

        return link

    async def delete_link(
        self,
        link_id: UUID,
        user_id: UUID | None = None,
    ) -> bool:
        """Delete a link. Returns True if deleted."""
        # Get the map_id for event publishing before deletion
        map_id = await self.db_session.select_value(GET_LINK_MAP_ID, link_id)
        if map_id is None:
            return False

        result = await self.db_session.execute(DELETE_LINK, link_id)
        deleted = result.num_rows > 0

        # Publish event
        if deleted and self.event_queue:
            event_id = await self.event_queue.get_next_event_id(map_id)
            event = MapEvent.link_deleted(
                event_id=event_id,
                map_id=map_id,
                link_id=link_id,
                user_id=user_id,
            )
            await self.event_queue.publish_event(event)

        return deleted


def provide_map_service(db_session: AsyncDriverAdapterBase, event_queue: MapEventQueue) -> MapService:
    """Provide MapService with injected database session and event queue."""
    return MapService(db_session, event_queue)
