from __future__ import annotations

from datetime import datetime
from uuid import UUID

import msgspec


CREATE_STMT = """\
CREATE TABLE IF NOT EXISTS link (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    map_id UUID NOT NULL REFERENCES map(id) ON DELETE CASCADE,
    source_node_id UUID NOT NULL REFERENCES node(id) ON DELETE CASCADE,
    target_node_id UUID NOT NULL REFERENCES node(id) ON DELETE CASCADE,
    wormhole_id INTEGER REFERENCES wormhole(id),
    mass_remaining BIGINT,
    eol_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (map_id, source_node_id, target_node_id)
);

CREATE INDEX IF NOT EXISTS idx_link_map_id ON link(map_id);
CREATE INDEX IF NOT EXISTS idx_link_source_node_id ON link(source_node_id);
CREATE INDEX IF NOT EXISTS idx_link_target_node_id ON link(target_node_id);
CREATE INDEX IF NOT EXISTS idx_link_wormhole_id ON link(wormhole_id);
CREATE INDEX IF NOT EXISTS idx_link_eol_at ON link(eol_at);
"""

INSERT_STMT = """\
INSERT INTO link (map_id, source_node_id, target_node_id, wormhole_id, mass_remaining, eol_at)
VALUES ($1, $2, $3, $4, $5, $6)
RETURNING id, map_id, source_node_id, target_node_id, wormhole_id, mass_remaining, eol_at, created_at, updated_at;
"""

UPDATE_STMT = """\
UPDATE link
SET wormhole_id = $2, mass_remaining = $3, eol_at = $4, updated_at = NOW()
WHERE id = $1
RETURNING id, map_id, source_node_id, target_node_id, wormhole_id, mass_remaining, eol_at, created_at, updated_at;
"""


class Link(msgspec.Struct):
    """Represents a wormhole connection between two nodes on a map."""

    map_id: UUID
    source_node_id: UUID
    target_node_id: UUID
    wormhole_id: int | None = None  # The "outgoing" wormhole type (K162 is always remote)
    mass_remaining: int | None = None  # Current mass remaining in kg
    eol_at: datetime | None = None  # End-of-life timestamp
    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_row(cls, row: tuple) -> Link:
        """Create a Link from a database row."""
        return cls(
            id=row[0],
            map_id=row[1],
            source_node_id=row[2],
            target_node_id=row[3],
            wormhole_id=row[4],
            mass_remaining=row[5],
            eol_at=row[6],
            created_at=row[7],
            updated_at=row[8],
        )

    @property
    def is_eol(self) -> bool:
        """Check if this wormhole is at end-of-life."""
        if self.eol_at is None:
            return False
        return datetime.now(self.eol_at.tzinfo) >= self.eol_at
