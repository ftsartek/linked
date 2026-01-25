from __future__ import annotations

from datetime import datetime
from uuid import UUID

import msgspec

INSERT_STMT = """\
INSERT INTO map
    (owner_id, name, description, is_public, public_read_only, edge_type, rankdir,
     auto_layout, node_sep, rank_sep, location_tracking_enabled)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
RETURNING
    id, owner_id, name, description, is_public, public_read_only, edge_type, rankdir,
    auto_layout, node_sep, rank_sep, location_tracking_enabled, date_created, date_updated,
    true AS edit_access;
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
    location_tracking_enabled = $11,
    date_updated = NOW()
WHERE id = $1
RETURNING id, owner_id, name, description, is_public, public_read_only, edge_type, rankdir,
    auto_layout, node_sep, rank_sep, location_tracking_enabled, date_created, date_updated,
    true AS edit_access;
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
    location_tracking_enabled: bool = True
    id: UUID | None = None
    date_created: datetime | None = None
    date_updated: datetime | None = None
    date_deleted: datetime | None = None
