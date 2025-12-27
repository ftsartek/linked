from __future__ import annotations

import msgspec


CREATE_STMT = """\
CREATE TABLE IF NOT EXISTS map_user (
    map_id INTEGER NOT NULL REFERENCES map(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'viewer',
    PRIMARY KEY (map_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_map_user_user_id ON map_user(user_id);
CREATE INDEX IF NOT EXISTS idx_map_user_role ON map_user(role);
"""

INSERT_STMT = """\
INSERT INTO map_user (map_id, user_id, role)
VALUES ($1, $2, $3)
ON CONFLICT (map_id, user_id) DO UPDATE SET role = EXCLUDED.role;
"""

DELETE_STMT = """\
DELETE FROM map_user
WHERE map_id = $1 AND user_id = $2;
"""


class MapUser(msgspec.Struct):
    """Join table linking maps to user owners/collaborators."""

    map_id: int
    user_id: int
    role: str = "viewer"  # 'owner', 'editor', 'viewer'
