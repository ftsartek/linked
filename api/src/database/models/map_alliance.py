from __future__ import annotations

from uuid import UUID

import msgspec

INSERT_STMT = """\
INSERT INTO map_alliance (map_id, alliance_id, read_only)
VALUES ($1, $2, $3)
ON CONFLICT (map_id, alliance_id) DO UPDATE SET read_only = EXCLUDED.read_only;
"""

DELETE_STMT = """\
DELETE FROM map_alliance
WHERE map_id = $1 AND alliance_id = $2;
"""


class MapAlliance(msgspec.Struct):
    """Join table linking maps to alliance owners/collaborators."""

    map_id: UUID
    alliance_id: int
    read_only: bool = True
