from __future__ import annotations

from datetime import datetime

import msgspec


CREATE_STMT = """\
CREATE TABLE IF NOT EXISTS character (
    id BIGINT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    corporation_id BIGINT,
    alliance_id BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_character_user_id ON character(user_id);
CREATE INDEX IF NOT EXISTS idx_character_corporation_id ON character(corporation_id);
CREATE INDEX IF NOT EXISTS idx_character_alliance_id ON character(alliance_id);
CREATE INDEX IF NOT EXISTS idx_character_name ON character(name);
"""

INSERT_STMT = """\
INSERT INTO character (id, user_id, name, corporation_id, alliance_id)
VALUES ($1, $2, $3, $4, $5)
RETURNING id, user_id, name, corporation_id, alliance_id, created_at, updated_at;
"""

UPDATE_STMT = """\
UPDATE character
SET name = $2, corporation_id = $3, alliance_id = $4, updated_at = NOW()
WHERE id = $1
RETURNING id, user_id, name, corporation_id, alliance_id, created_at, updated_at;
"""


class Character(msgspec.Struct):
    """Represents an EVE Online character linked to a platform user."""

    id: int  # EVE character_id
    user_id: int
    name: str
    corporation_id: int | None = None
    alliance_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_esi_data(cls, character_id: int, user_id: int, data: dict) -> Character:
        """Create a Character from ESI public character data."""
        return cls(
            id=character_id,
            user_id=user_id,
            name=data["name"],
            corporation_id=data.get("corporation_id"),
            alliance_id=data.get("alliance_id"),
        )

    @classmethod
    def from_row(cls, row: tuple) -> Character:
        """Create a Character from a database row."""
        return cls(
            id=row[0],
            user_id=row[1],
            name=row[2],
            corporation_id=row[3],
            alliance_id=row[4],
            created_at=row[5],
            updated_at=row[6],
        )
