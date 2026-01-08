from __future__ import annotations

from datetime import datetime
from uuid import UUID

import msgspec

from utils.enums import LifetimeStatus

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
    date_deleted: datetime | None = None

    @property
    def is_eol(self) -> bool:
        """Check if this wormhole is at end-of-life."""
        return self.lifetime_status == LifetimeStatus.EOL
