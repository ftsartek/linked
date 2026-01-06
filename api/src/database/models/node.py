from __future__ import annotations

from datetime import datetime
from uuid import UUID

import msgspec

CREATE_STMT = """\
CREATE TABLE IF NOT EXISTS node (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    map_id UUID NOT NULL REFERENCES map(id) ON DELETE CASCADE,
    system_id INTEGER NOT NULL REFERENCES system(id),
    pos_x REAL NOT NULL DEFAULT 0,
    pos_y REAL NOT NULL DEFAULT 0,
    locked BOOLEAN NOT NULL DEFAULT FALSE,
    label TEXT,
    date_created TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    date_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    date_deleted TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_node_map_id ON node(map_id);
CREATE INDEX IF NOT EXISTS idx_node_system_id ON node(system_id);
CREATE INDEX IF NOT EXISTS idx_node_date_deleted ON node(date_deleted);

-- Partial unique index: only enforce uniqueness for real systems (positive IDs)
-- Unidentified systems (negative IDs) can have multiple nodes per map
CREATE UNIQUE INDEX IF NOT EXISTS idx_node_map_system_unique
ON node(map_id, system_id)
WHERE system_id > 0 AND date_deleted IS NULL;
"""

INSERT_STMT = """\
INSERT INTO node (map_id, system_id, pos_x, pos_y, label)
VALUES ($1, $2, $3, $4, $5)
RETURNING id, map_id, system_id, pos_x, pos_y, label, date_created, date_updated;
"""

UPDATE_STMT = """\
UPDATE node
SET pos_x = $2, pos_y = $3, label = $4, date_updated = NOW()
WHERE id = $1
RETURNING id, map_id, system_id, pos_x, pos_y, label, date_created, date_updated;
"""


class Node(msgspec.Struct):
    """Represents a solar system node on a map."""

    map_id: UUID
    system_id: int
    pos_x: float = 0.0
    pos_y: float = 0.0
    label: str | None = None
    id: UUID | None = None
    date_created: datetime | None = None
    date_updated: datetime | None = None
    date_deleted: datetime | None = None
