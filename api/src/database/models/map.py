from __future__ import annotations

from datetime import datetime
from uuid import UUID

import msgspec

from utils.datetime import ensure_utc

CREATE_STMT = """\
CREATE TABLE IF NOT EXISTS map (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    is_public BOOLEAN NOT NULL DEFAULT FALSE,
    date_created TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    date_updated TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_map_owner_id ON map(owner_id);
CREATE INDEX IF NOT EXISTS idx_map_name ON map(name);
CREATE INDEX IF NOT EXISTS idx_map_is_public ON map(is_public);
CREATE INDEX IF NOT EXISTS idx_map_date_created ON map(date_created);
"""

INSERT_STMT = """\
INSERT INTO map (owner_id, name, description, is_public)
VALUES ($1, $2, $3, $4)
RETURNING id, owner_id, name, description, is_public, date_created, date_updated;
"""

UPDATE_STMT = """\
UPDATE map
SET name = $2, description = $3, is_public = $4, date_updated = NOW()
WHERE id = $1
RETURNING id, owner_id, name, description, is_public, date_created, date_updated;
"""


class Map(msgspec.Struct):
    """Represents a wormhole mapping session/map."""

    owner_id: UUID
    name: str
    description: str | None = None
    is_public: bool = False
    id: UUID | None = None
    date_created: datetime | None = None
    date_updated: datetime | None = None

    @classmethod
    def from_row(cls, row: tuple) -> Map:
        """Create a Map from a database row."""
        return cls(
            id=row[0],
            owner_id=row[1],
            name=row[2],
            description=row[3],
            is_public=row[4],
            date_created=ensure_utc(row[5]),
            date_updated=ensure_utc(row[6]),
        )
