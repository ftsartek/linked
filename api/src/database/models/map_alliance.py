from __future__ import annotations

from uuid import UUID

import msgspec

CREATE_STMT = """\
CREATE TABLE IF NOT EXISTS map_alliance (
    map_id UUID NOT NULL REFERENCES map(id) ON DELETE CASCADE,
    alliance_id BIGINT NOT NULL REFERENCES alliance(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'viewer',
    PRIMARY KEY (map_id, alliance_id)
);

CREATE INDEX IF NOT EXISTS idx_map_alliance_alliance_id ON map_alliance(alliance_id);
CREATE INDEX IF NOT EXISTS idx_map_alliance_role ON map_alliance(role);
"""

INSERT_STMT = """\
INSERT INTO map_alliance (map_id, alliance_id, role)
VALUES ($1, $2, $3)
ON CONFLICT (map_id, alliance_id) DO UPDATE SET role = EXCLUDED.role;
"""

DELETE_STMT = """\
DELETE FROM map_alliance
WHERE map_id = $1 AND alliance_id = $2;
"""


class MapAlliance(msgspec.Struct):
    """Join table linking maps to alliance owners/collaborators."""

    map_id: UUID
    alliance_id: int
    role: str = "viewer"  # 'owner', 'editor', 'viewer'
