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
from routes.maps.queries import (
    CHECK_ACCESS,
    CHECK_EDIT_ACCESS,
    DELETE_MAP,
    GET_K162_ID,
    GET_LINK_ENRICHED,
    GET_MAP,
    GET_MAP_LINKS,
    GET_MAP_NODES,
    GET_NODE_ENRICHED,
    GET_USER_CHARACTER,
    INSERT_LINK,
    INSERT_NODE,
    LIST_ALLIANCE_MAPS,
    LIST_CORPORATION_MAPS,
    LIST_OWNED_MAPS,
    LIST_SHARED_MAPS,
    UPDATE_MAP,
)


class MapService:
    """Map management business logic."""

    def __init__(self, db_session: AsyncDriverAdapterBase) -> None:
        self.db_session = db_session

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
    ) -> EnrichedNodeInfo:
        """Create a new node on the map."""
        node_id = await self.db_session.select_value(
            INSERT_NODE,
            map_id,
            system_id,
            pos_x,
            pos_y,
        )
        return await self.db_session.select_one(
            GET_NODE_ENRICHED,
            node_id,
            schema_type=EnrichedNodeInfo,
        )

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


def provide_map_service(db_session: AsyncDriverAdapterBase) -> MapService:
    """Provide MapService with injected database session."""
    return MapService(db_session)
