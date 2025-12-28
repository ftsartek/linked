from __future__ import annotations

from datetime import datetime
from uuid import UUID

import msgspec

from utils.datetime import ensure_utc

from ..enums import LifetimeStatus, MassStatus

CREATE_STMT = """
CREATE TABLE IF NOT EXISTS link (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    map_id UUID NOT NULL REFERENCES map(id) ON DELETE CASCADE,
    source_node_id UUID NOT NULL REFERENCES node(id) ON DELETE CASCADE,
    target_node_id UUID NOT NULL REFERENCES node(id) ON DELETE CASCADE,
    wormhole_id INTEGER REFERENCES wormhole(id),
    lifetime_status TEXT NOT NULL DEFAULT 'stable',
    date_lifetime_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    mass_usage BIGINT NOT NULL DEFAULT 0,
    date_mass_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    date_created TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    date_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (map_id, source_node_id, target_node_id)
);

CREATE INDEX IF NOT EXISTS idx_link_map_id ON link(map_id);
CREATE INDEX IF NOT EXISTS idx_link_source_node_id ON link(source_node_id);
CREATE INDEX IF NOT EXISTS idx_link_target_node_id ON link(target_node_id);
CREATE INDEX IF NOT EXISTS idx_link_wormhole_id ON link(wormhole_id);
CREATE INDEX IF NOT EXISTS idx_link_lifetime_status ON link(lifetime_status);
CREATE INDEX IF NOT EXISTS idx_link_mass_usage ON link(mass_usage);
"""

INSERT_STMT = """
INSERT INTO link (map_id, source_node_id, target_node_id, wormhole_id,
                  lifetime_status, date_lifetime_updated, mass_usage, date_mass_updated)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
RETURNING id, map_id, source_node_id, target_node_id, wormhole_id,
          lifetime_status, date_lifetime_updated, mass_usage, date_mass_updated,
          date_created, date_updated;
"""

UPDATE_STMT = """
UPDATE link
SET wormhole_id = $2,
    lifetime_status = $3, date_lifetime_updated = $4,
    mass_usage = $5, date_mass_updated = $6,
    date_updated = NOW()
WHERE id = $1
RETURNING id, map_id, source_node_id, target_node_id, wormhole_id,
          lifetime_status, date_lifetime_updated, mass_usage, date_mass_updated,
          date_created, date_updated;
"""

UPDATE_LIFETIME_STATUS_STMT = """
UPDATE link
SET lifetime_status = $2, date_lifetime_updated = $3, date_updated = NOW()
WHERE id = $1
RETURNING id, lifetime_status, date_lifetime_updated;
"""

UPDATE_mass_usage_STMT = """
UPDATE link
SET mass_usage = $2, date_mass_updated = $3, date_updated = NOW()
WHERE id = $1
RETURNING id, mass_usage, date_mass_updated;
"""


class Link(msgspec.Struct):
    """Represents a wormhole connection between two nodes on a map."""

    map_id: UUID
    source_node_id: UUID
    target_node_id: UUID
    wormhole_id: int | None = None  # The "outgoing" wormhole type (K162 is always remote)
    lifetime_status: LifetimeStatus = LifetimeStatus.STABLE
    date_lifetime_updated: datetime | None = None
    mass_usage: int = 0
    date_mass_updated: datetime | None = None
    id: UUID | None = None
    date_created: datetime | None = None
    date_updated: datetime | None = None

    @classmethod
    def from_row(cls, row: tuple) -> Link:
        """Create a Link from a database row."""
        return cls(
            id=row[0],
            map_id=row[1],
            source_node_id=row[2],
            target_node_id=row[3],
            wormhole_id=row[4],
            lifetime_status=LifetimeStatus(row[5]),
            date_lifetime_updated=ensure_utc(row[6]),
            mass_usage=MassStatus(row[7]),
            date_mass_updated=ensure_utc(row[8]),
            date_created=ensure_utc(row[9]),
            date_updated=ensure_utc(row[10]),
        )

    @property
    def is_eol(self) -> bool:
        """Check if this wormhole is at end-of-life."""
        return self.lifetime_status == LifetimeStatus.EOL
