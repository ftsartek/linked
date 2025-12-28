from __future__ import annotations

from uuid import UUID

import msgspec

CREATE_STMT = """\
CREATE TABLE IF NOT EXISTS map_corporation (
    map_id UUID NOT NULL REFERENCES map(id) ON DELETE CASCADE,
    corporation_id BIGINT NOT NULL REFERENCES corporation(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'viewer',
    PRIMARY KEY (map_id, corporation_id)
);

CREATE INDEX IF NOT EXISTS idx_map_corporation_corporation_id ON map_corporation(corporation_id);
CREATE INDEX IF NOT EXISTS idx_map_corporation_role ON map_corporation(role);
"""

INSERT_STMT = """\
INSERT INTO map_corporation (map_id, corporation_id, role)
VALUES ($1, $2, $3)
ON CONFLICT (map_id, corporation_id) DO UPDATE SET role = EXCLUDED.role;
"""

DELETE_STMT = """\
DELETE FROM map_corporation
WHERE map_id = $1 AND corporation_id = $2;
"""


class MapCorporation(msgspec.Struct):
    """Join table linking maps to corporation owners/collaborators."""

    map_id: UUID
    corporation_id: int
    role: str = "viewer"  # 'owner', 'editor', 'viewer'
