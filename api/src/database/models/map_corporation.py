from __future__ import annotations

from uuid import UUID

import msgspec

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
