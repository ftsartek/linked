"""Base service with shared access control functionality for route handlers."""

from __future__ import annotations

from uuid import UUID

import msgspec
from sqlspec import AsyncDriverAdapterBase

# SQL Queries for access control
GET_USER_CHARACTER = """
SELECT c.corporation_id, c.alliance_id, u.primary_character_id
FROM "user" u
LEFT JOIN character c ON c.id = u.primary_character_id
WHERE u.id = $1;
"""

GET_USER_CHARACTER_IDS = """
SELECT id FROM character WHERE user_id = $1;
"""

CHECK_ACCESS = """
SELECT EXISTS(
    SELECT 1 FROM map WHERE id = $1 AND (owner_id = $2 OR is_public = true)
    UNION
    SELECT 1 FROM map_character WHERE map_id = $1
        AND character_id IN (SELECT id FROM character WHERE user_id = $2)
    UNION
    SELECT 1 FROM map_corporation WHERE map_id = $1 AND corporation_id = $3
    UNION
    SELECT 1 FROM map_alliance WHERE map_id = $1 AND alliance_id = $4
    UNION
    SELECT 1 FROM map_subscription ms
        JOIN map m ON ms.map_id = m.id
        WHERE ms.map_id = $1 AND ms.user_id = $2 AND m.is_public = true
);
"""

CHECK_EDIT_ACCESS = """
SELECT CASE
    WHEN m.owner_id = $2 THEN true
    WHEN mch.map_id IS NOT NULL THEN NOT mch.read_only
    WHEN mc.map_id IS NOT NULL THEN NOT mc.read_only
    WHEN ma.map_id IS NOT NULL THEN NOT ma.read_only
    WHEN ms.map_id IS NOT NULL AND m.is_public = true THEN NOT m.public_read_only
    ELSE false
END
FROM map m
LEFT JOIN map_character mch ON mch.map_id = m.id
    AND mch.character_id IN (SELECT id FROM character WHERE user_id = $2)
LEFT JOIN map_corporation mc ON mc.map_id = m.id AND mc.corporation_id = $3
LEFT JOIN map_alliance ma ON ma.map_id = m.id AND ma.alliance_id = $4
LEFT JOIN map_subscription ms ON ms.map_id = m.id AND ms.user_id = $2
WHERE m.id = $1;
"""


class _UserCharacter(msgspec.Struct):
    """User character info for context lookups."""

    corporation_id: int | None
    alliance_id: int | None
    primary_character_id: int | None


class _UserCharacterId(msgspec.Struct):
    """User character ID for access checks."""

    id: int


class CharacterContext(msgspec.Struct):
    """Character context for access checks."""

    user_id: UUID
    corporation_id: int | None
    alliance_id: int | None
    primary_character_id: int | None = None
    character_ids: list[int] = []


class RouteBaseService:
    """Base service providing shared access control functionality.

    Services that need character context and map access checking
    should inherit from this class.
    """

    def __init__(self, db_session: AsyncDriverAdapterBase) -> None:
        self.db_session = db_session

    async def get_character_context(self, user_id: UUID) -> CharacterContext:
        """Get the user's character context for access checks."""
        row = await self.db_session.select_one_or_none(GET_USER_CHARACTER, user_id, schema_type=_UserCharacter)
        char_rows = await self.db_session.select(GET_USER_CHARACTER_IDS, user_id, schema_type=_UserCharacterId)
        character_ids = [r.id for r in char_rows]

        if row is None:
            return CharacterContext(
                user_id=user_id,
                corporation_id=None,
                alliance_id=None,
                primary_character_id=None,
                character_ids=character_ids,
            )
        return CharacterContext(
            user_id=user_id,
            corporation_id=row.corporation_id,
            alliance_id=row.alliance_id,
            primary_character_id=row.primary_character_id,
            character_ids=character_ids,
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
