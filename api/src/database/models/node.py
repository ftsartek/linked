from __future__ import annotations

from datetime import datetime
from uuid import UUID

import msgspec

from utils.datetime import ensure_utc

CREATE_STMT = """\
CREATE TABLE IF NOT EXISTS node (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    map_id UUID NOT NULL REFERENCES map(id) ON DELETE CASCADE,
    system_id INTEGER NOT NULL REFERENCES system(id),
    pos_x REAL NOT NULL DEFAULT 0,
    pos_y REAL NOT NULL DEFAULT 0,
    label TEXT,
    date_created TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    date_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (map_id, system_id)
);

CREATE INDEX IF NOT EXISTS idx_node_map_id ON node(map_id);
CREATE INDEX IF NOT EXISTS idx_node_system_id ON node(system_id);
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

    @classmethod
    def from_row(cls, row: tuple) -> Node:
        """Create a Node from a database row."""
        return cls(
            id=row[0],
            map_id=row[1],
            system_id=row[2],
            pos_x=row[3],
            pos_y=row[4],
            label=row[5],
            date_created=ensure_utc(row[6]),
            date_updated=ensure_utc(row[7]),
        )
