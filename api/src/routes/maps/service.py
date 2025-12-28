from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlspec import AsyncDriverAdapterBase

from database.models.link import Link
from database.models.map import INSERT_STMT as MAP_INSERT
from database.models.map import Map
from database.models.map_alliance import DELETE_STMT as MAP_ALLIANCE_DELETE
from database.models.map_alliance import INSERT_STMT as MAP_ALLIANCE_INSERT
from database.models.map_corporation import DELETE_STMT as MAP_CORPORATION_DELETE
from database.models.map_corporation import INSERT_STMT as MAP_CORPORATION_INSERT
from database.models.map_user import DELETE_STMT as MAP_USER_DELETE
from database.models.map_user import INSERT_STMT as MAP_USER_INSERT
from database.models.node import Node


@dataclass
class MapInfo:
    """Map information for API responses."""

    id: UUID
    owner_id: UUID
    name: str
    description: str | None
    is_public: bool
    created_at: datetime
    updated_at: datetime


@dataclass
class NodeInfo:
    """Node information for API responses."""

    id: UUID
    system_id: int
    pos_x: float
    pos_y: float
    label: str | None


@dataclass
class LinkInfo:
    """Link information for API responses."""

    id: UUID
    source_node_id: UUID
    target_node_id: UUID
    wormhole_id: int | None
    mass_remaining: int | None
    eol_at: datetime | None


@dataclass
class CharacterContext:
    """Character context for access checks."""

    user_id: UUID
    corporation_id: int | None
    alliance_id: int | None


@dataclass
class MapDetailResponse:
    """Full map with nodes and links."""

    map: MapInfo
    nodes: list[NodeInfo]
    links: list[LinkInfo]


@dataclass
class MapListResponse:
    """List of maps."""

    maps: list[MapInfo]


LIST_OWNED_MAPS = """
SELECT id, owner_id, name, description, is_public, created_at, updated_at
FROM map
WHERE owner_id = $1
ORDER BY updated_at DESC;
"""

LIST_SHARED_MAPS = """
SELECT m.id, m.owner_id, m.name, m.description, m.is_public, m.created_at, m.updated_at
FROM map m
JOIN map_user mu ON m.id = mu.map_id
WHERE mu.user_id = $1
ORDER BY m.updated_at DESC;
"""

LIST_CORPORATION_MAPS = """
SELECT m.id, m.owner_id, m.name, m.description, m.is_public, m.created_at, m.updated_at
FROM map m
JOIN map_corporation mc ON m.id = mc.map_id
WHERE mc.corporation_id = $1
ORDER BY m.updated_at DESC;
"""

LIST_ALLIANCE_MAPS = """
SELECT m.id, m.owner_id, m.name, m.description, m.is_public, m.created_at, m.updated_at
FROM map m
JOIN map_alliance ma ON m.id = ma.map_id
WHERE ma.alliance_id = $1
ORDER BY m.updated_at DESC;
"""

GET_MAP = """
SELECT id, owner_id, name, description, is_public, created_at, updated_at
FROM map
WHERE id = $1;
"""

GET_MAP_NODES = """
SELECT id, system_id, pos_x, pos_y, label
FROM node
WHERE map_id = $1
ORDER BY id;
"""

GET_MAP_LINKS = """
SELECT id, source_node_id, target_node_id, wormhole_id, mass_remaining, eol_at
FROM link
WHERE map_id = $1
ORDER BY id;
"""

CHECK_ACCESS = """
SELECT EXISTS(
    SELECT 1 FROM map WHERE id = $1 AND (owner_id = $2 OR is_public = true)
    UNION
    SELECT 1 FROM map_user WHERE map_id = $1 AND user_id = $2
    UNION
    SELECT 1 FROM map_corporation WHERE map_id = $1 AND corporation_id = $3
    UNION
    SELECT 1 FROM map_alliance WHERE map_id = $1 AND alliance_id = $4
);
"""

@dataclass
class UserCharacter:
    corporation_id: int | None
    alliance_id: int | None

GET_USER_CHARACTER = """
SELECT corporation_id, alliance_id
FROM character
WHERE user_id = $1
LIMIT 1;
"""

UPDATE_MAP = """
UPDATE map
SET name = COALESCE($2, name),
    description = COALESCE($3, description),
    is_public = COALESCE($4, is_public),
    updated_at = NOW()
WHERE id = $1
RETURNING id, owner_id, name, description, is_public, created_at, updated_at;
"""

DELETE_MAP = """
DELETE FROM map WHERE id = $1;
"""


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

    async def list_corporation_maps(self, corporation_id: int) -> list[MapInfo]:
        """List maps shared with the corporation."""
        return await self.db_session.select(
            LIST_CORPORATION_MAPS,
            corporation_id,
            schema_type=MapInfo,
        )

    async def list_alliance_maps(self, alliance_id: int) -> list[MapInfo]:
        """List maps shared with the alliance."""
        return await self.db_session.select(
            LIST_ALLIANCE_MAPS,
            alliance_id,
            schema_type=MapInfo,
        )

    async def get_map(self, map_id: UUID) -> MapInfo | None:
        """Get a map by ID."""
        return await self.db_session.select_one_or_none(
            GET_MAP,
            map_id,
            schema_type=MapInfo,
        )

    async def get_map_nodes(self, map_id: UUID) -> list[NodeInfo]:
        """Get all nodes for a map."""
        return await self.db_session.select(
            GET_MAP_NODES,
            map_id,
            schema_type=NodeInfo,
        )

    async def get_map_links(self, map_id: UUID) -> list[LinkInfo]:
        """Get all links for a map."""
        return await self.db_session.select(
            GET_MAP_LINKS,
            map_id,
            schema_type=LinkInfo,
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

    async def get_character_context(self, user_id: UUID) -> CharacterContext:
        """Get the user's character context for access checks."""
        row = await self.db_session.select_one_or_none(
            GET_USER_CHARACTER,
            user_id,
            schema_type=UserCharacter
        )
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
        return result.rowcount > 0

    async def is_owner(self, map_id: UUID, user_id: UUID) -> bool:
        """Check if user is the owner of the map."""
        map_info = await self.get_map(map_id)
        return map_info is not None and map_info.owner_id == user_id

    # User access management

    async def add_user_access(
        self,
        map_id: UUID,
        user_id: UUID,
        role: str = "viewer",
    ) -> None:
        """Add or update user access to a map."""
        await self.db_session.execute(MAP_USER_INSERT, map_id, user_id, role)

    async def remove_user_access(self, map_id: UUID, user_id: UUID) -> bool:
        """Remove user access from a map. Returns True if removed."""
        result = await self.db_session.execute(MAP_USER_DELETE, map_id, user_id)
        return result.rowcount > 0

    # Corporation access management

    async def add_corporation_access(
        self,
        map_id: UUID,
        corporation_id: int,
        role: str = "viewer",
    ) -> None:
        """Add or update corporation access to a map."""
        await self.db_session.execute(MAP_CORPORATION_INSERT, map_id, corporation_id, role)

    async def remove_corporation_access(self, map_id: UUID, corporation_id: int) -> bool:
        """Remove corporation access from a map. Returns True if removed."""
        result = await self.db_session.execute(MAP_CORPORATION_DELETE, map_id, corporation_id)
        return result.rowcount > 0

    # Alliance access management

    async def add_alliance_access(
        self,
        map_id: UUID,
        alliance_id: int,
        role: str = "viewer",
    ) -> None:
        """Add or update alliance access to a map."""
        await self.db_session.execute(MAP_ALLIANCE_INSERT, map_id, alliance_id, role)

    async def remove_alliance_access(self, map_id: UUID, alliance_id: int) -> bool:
        """Remove alliance access from a map. Returns True if removed."""
        result = await self.db_session.execute(MAP_ALLIANCE_DELETE, map_id, alliance_id)
        return result.rowcount > 0


def provide_map_service(db_session: AsyncDriverAdapterBase) -> MapService:
    """Provide MapService with injected database session."""
    return MapService(db_session)
