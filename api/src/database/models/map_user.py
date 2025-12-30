from __future__ import annotations

from uuid import UUID

import msgspec

CREATE_STMT = """\
CREATE TABLE IF NOT EXISTS map_user (
    map_id UUID NOT NULL REFERENCES map(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    read_only BOOLEAN NOT NULL DEFAULT true,
    PRIMARY KEY (map_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_map_user_user_id ON map_user(user_id);
CREATE INDEX IF NOT EXISTS idx_map_user_read_only ON map_user(read_only);
"""

INSERT_STMT = """\
INSERT INTO map_user (map_id, user_id, read_only)
VALUES ($1, $2, $3)
ON CONFLICT (map_id, user_id) DO UPDATE SET read_only = EXCLUDED.read_only;
"""

DELETE_STMT = """\
DELETE FROM map_user
WHERE map_id = $1 AND user_id = $2;
"""


class MapUser(msgspec.Struct):
    """Join table linking maps to user owners/collaborators."""

    map_id: UUID
    user_id: UUID
    read_only: bool = True
