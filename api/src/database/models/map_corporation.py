from __future__ import annotations

from uuid import UUID

import msgspec

CREATE_STMT = """\
CREATE TABLE IF NOT EXISTS map_corporation (
    map_id UUID NOT NULL REFERENCES map(id) ON DELETE CASCADE,
    corporation_id BIGINT NOT NULL REFERENCES corporation(id) ON DELETE CASCADE,
    read_only BOOLEAN NOT NULL DEFAULT true,
    PRIMARY KEY (map_id, corporation_id)
);

CREATE INDEX IF NOT EXISTS idx_map_corporation_corporation_id ON map_corporation(corporation_id);
CREATE INDEX IF NOT EXISTS idx_map_corporation_read_only ON map_corporation(read_only);
"""

INSERT_STMT = """\
INSERT INTO map_corporation (map_id, corporation_id, read_only)
VALUES ($1, $2, $3)
ON CONFLICT (map_id, corporation_id) DO UPDATE SET read_only = EXCLUDED.read_only;
"""

DELETE_STMT = """\
DELETE FROM map_corporation
WHERE map_id = $1 AND corporation_id = $2;
"""


class MapCorporation(msgspec.Struct):
    """Join table linking maps to corporation owners/collaborators."""

    map_id: UUID
    corporation_id: int
    read_only: bool = True
