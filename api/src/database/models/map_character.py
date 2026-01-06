from __future__ import annotations

from uuid import UUID

import msgspec

CREATE_STMT = """\
CREATE TABLE IF NOT EXISTS map_character (
    map_id UUID NOT NULL REFERENCES map(id) ON DELETE CASCADE,
    character_id BIGINT NOT NULL REFERENCES character(id) ON DELETE CASCADE,
    read_only BOOLEAN NOT NULL DEFAULT true,
    PRIMARY KEY (map_id, character_id)
);

CREATE INDEX IF NOT EXISTS idx_map_character_character_id ON map_character(character_id);
"""

INSERT_STMT = """\
INSERT INTO map_character (map_id, character_id, read_only)
VALUES ($1, $2, $3)
ON CONFLICT (map_id, character_id) DO UPDATE SET read_only = EXCLUDED.read_only;
"""

DELETE_STMT = """\
DELETE FROM map_character
WHERE map_id = $1 AND character_id = $2;
"""

SELECT_BY_MAP_STMT = """\
SELECT mc.character_id, c.name, mc.read_only
FROM map_character mc
JOIN character c ON c.id = mc.character_id
WHERE mc.map_id = $1
ORDER BY c.name;
"""


class MapCharacter(msgspec.Struct):
    """Join table linking maps to characters with access."""

    map_id: UUID
    character_id: int
    read_only: bool = True
