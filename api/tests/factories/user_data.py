"""Factories for user and character test data."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from sqlspec.adapters.asyncpg.driver import AsyncpgDriver

from tests.factories.static_data import (
    TEST_ALLIANCE_ID,
    TEST_CHARACTER_ID,
    TEST_CHARACTER_NAME,
    TEST_CORPORATION_ID,
)


async def create_test_user(session: AsyncpgDriver, user_id: UUID | None = None) -> UUID:
    """Create a test user in the database.

    Args:
        session: Database session
        user_id: Optional specific user ID, generates one if not provided

    Returns:
        The user's UUID
    """
    if user_id is None:
        user_id = uuid4()

    await session.execute(
        'INSERT INTO "user" (id) VALUES ($1) ON CONFLICT (id) DO NOTHING',
        [user_id],
    )
    return user_id


async def create_test_character(
    session: AsyncpgDriver,
    user_id: UUID,
    character_id: int = TEST_CHARACTER_ID,
    name: str = TEST_CHARACTER_NAME,
    corporation_id: int = TEST_CORPORATION_ID,
    alliance_id: int | None = TEST_ALLIANCE_ID,
) -> int:
    """Create a test character associated with a user.

    Args:
        session: Database session
        user_id: User to associate the character with
        character_id: EVE character ID
        name: Character name
        corporation_id: Corporation ID
        alliance_id: Alliance ID (optional)

    Returns:
        The character ID
    """
    await session.execute(
        """
        INSERT INTO character (id, user_id, name, corporation_id, alliance_id)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (id) DO UPDATE SET
            user_id = EXCLUDED.user_id,
            name = EXCLUDED.name,
            corporation_id = EXCLUDED.corporation_id,
            alliance_id = EXCLUDED.alliance_id
        """,
        [character_id, user_id, name, corporation_id, alliance_id],
    )
    return character_id


async def create_test_user_with_character(
    session: AsyncpgDriver,
    user_id: UUID | None = None,
) -> tuple[UUID, int]:
    """Create a test user with an associated character.

    This is a convenience function that creates both user and character
    with the default test values.

    Args:
        session: Database session
        user_id: Optional specific user ID

    Returns:
        Tuple of (user_id, character_id)
    """
    uid = await create_test_user(session, user_id)
    cid = await create_test_character(session, uid)
    return uid, cid
