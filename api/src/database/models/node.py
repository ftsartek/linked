from __future__ import annotations

from datetime import datetime
from uuid import UUID

import msgspec

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
