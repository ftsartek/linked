from __future__ import annotations

from datetime import datetime
from uuid import UUID

import msgspec

CREATE_STMT = """\
CREATE TABLE IF NOT EXISTS map (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    is_public BOOLEAN NOT NULL DEFAULT FALSE,
    public_read_only BOOLEAN NOT NULL DEFAULT TRUE,
    edge_type TEXT NOT NULL DEFAULT 'default',
    rankdir TEXT NOT NULL DEFAULT 'TB',
    auto_layout BOOLEAN NOT NULL DEFAULT FALSE,
    node_sep INTEGER NOT NULL DEFAULT 80,
    rank_sep INTEGER NOT NULL DEFAULT 60,
    date_created TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    date_updated TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_map_owner_id ON map(owner_id);
CREATE INDEX IF NOT EXISTS idx_map_name ON map(name);
CREATE INDEX IF NOT EXISTS idx_map_is_public ON map(is_public);
CREATE INDEX IF NOT EXISTS idx_map_date_created ON map(date_created);
"""

INSERT_STMT = """\
INSERT INTO map
    (owner_id, name, description, is_public, public_read_only, edge_type, rankdir, auto_layout, node_sep, rank_sep)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
RETURNING
    id, owner_id, name, description, is_public, public_read_only, edge_type,
    rankdir, auto_layout, node_sep, rank_sep, date_created, date_updated;
"""

UPDATE_STMT = """\
UPDATE map
SET name = $2,
    description = $3,
    is_public = $4,
    public_read_only = $5,
    edge_type = $6,
    rankdir = $7,
    auto_layout = $8,
    node_sep = $9,
    rank_sep = $10,
    date_updated = NOW()
WHERE id = $1
RETURNING id, owner_id, name, description, is_public, public_read_only, edge_type,
    rankdir, auto_layout, node_sep, rank_sep, date_created, date_updated;
"""


class Map(msgspec.Struct):
    """Represents a wormhole mapping session/map."""

    owner_id: UUID
    name: str
    description: str | None = None
    is_public: bool = False
    public_read_only: bool = True
    edge_type: str = "default"
    rankdir: str = "TB"
    auto_layout: bool = False
    node_sep: int = 50
    rank_sep: int = 50
    id: UUID | None = None
    date_created: datetime | None = None
    date_updated: datetime | None = None
