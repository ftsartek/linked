from __future__ import annotations

from datetime import datetime

import msgspec


CREATE_STMT = """\
CREATE TABLE IF NOT EXISTS map (
    id SERIAL PRIMARY KEY,
    owner_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    is_public BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_map_owner_id ON map(owner_id);
CREATE INDEX IF NOT EXISTS idx_map_name ON map(name);
CREATE INDEX IF NOT EXISTS idx_map_is_public ON map(is_public);
CREATE INDEX IF NOT EXISTS idx_map_created_at ON map(created_at);
"""

INSERT_STMT = """\
INSERT INTO map (owner_id, name, description, is_public)
VALUES ($1, $2, $3, $4)
RETURNING id, owner_id, name, description, is_public, created_at, updated_at;
"""

UPDATE_STMT = """\
UPDATE map
SET name = $2, description = $3, is_public = $4, updated_at = NOW()
WHERE id = $1
RETURNING id, owner_id, name, description, is_public, created_at, updated_at;
"""


class Map(msgspec.Struct):
    """Represents a wormhole mapping session/map."""

    owner_id: int
    name: str
    description: str | None = None
    is_public: bool = False
    id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_row(cls, row: tuple) -> Map:
        """Create a Map from a database row."""
        return cls(
            id=row[0],
            owner_id=row[1],
            name=row[2],
            description=row[3],
            is_public=row[4],
            created_at=row[5],
            updated_at=row[6],
        )
