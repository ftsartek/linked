from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlspec import AsyncDriverAdapterBase


@dataclass
class CharacterInfo:
    """Character information for API responses."""

    id: int
    name: str
    corporation_id: int | None
    alliance_id: int | None


@dataclass
class CharacterWithOwner:
    """Character with owner info for ownership verification."""

    id: int
    user_id: UUID
    name: str
    corporation_id: int | None
    alliance_id: int | None


@dataclass
class CharacterListResponse:
    """List of characters response."""

    characters: list[CharacterInfo]


# SQL Statements
GET_USER_CHARACTERS = """\
SELECT id, name, corporation_id, alliance_id
FROM character
WHERE user_id = $1
ORDER BY name;
"""

GET_CHARACTER_BY_ID = """\
SELECT id, user_id, name, corporation_id, alliance_id
FROM character
WHERE id = $1;
"""

COUNT_USER_CHARACTERS = """\
SELECT COUNT(*) FROM character WHERE user_id = $1;
"""

DELETE_CHARACTER = """\
DELETE FROM character WHERE id = $1 AND user_id = $2;
"""


class UserService:
    """User management business logic."""

    def __init__(self, db_session: AsyncDriverAdapterBase) -> None:
        self.db_session = db_session

    async def get_user_characters(self, user_id: UUID) -> list[CharacterInfo]:
        """Get all characters for a user."""
        return await self.db_session.select(
            GET_USER_CHARACTERS,
            user_id,
            schema_type=CharacterInfo,
        )

    async def get_character(
        self,
        character_id: int,
        user_id: UUID,
    ) -> CharacterInfo | None:
        """Get character if it belongs to user, None otherwise."""
        result = await self.db_session.select_one_or_none(
            GET_CHARACTER_BY_ID,
            character_id,
            schema_type=CharacterWithOwner,
        )
        if result is None or result.user_id != user_id:
            return None
        return CharacterInfo(
            id=result.id,
            name=result.name,
            corporation_id=result.corporation_id,
            alliance_id=result.alliance_id,
        )

    async def count_user_characters(self, user_id: UUID) -> int:
        """Count characters owned by user."""
        return await self.db_session.select_value(
            COUNT_USER_CHARACTERS,
            user_id,
        )

    async def delete_character(
        self,
        character_id: int,
        user_id: UUID,
    ) -> bool:
        """Delete character if it belongs to user. Returns True if deleted."""
        result = await self.db_session.execute(
            DELETE_CHARACTER,
            character_id,
            user_id,
        )
        return result.rowcount > 0

    async def can_delete_character(self, user_id: UUID) -> bool:
        """Check if user has more than one character."""
        count = await self.count_user_characters(user_id)
        return count > 1


async def provide_user_service(db_session: AsyncDriverAdapterBase) -> UserService:
    """Provide UserService with injected database session."""
    return UserService(db_session)
