from __future__ import annotations

from uuid import UUID

import msgspec

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
