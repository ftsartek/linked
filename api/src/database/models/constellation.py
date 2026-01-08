from __future__ import annotations

import msgspec

INSERT_STMT = """
INSERT INTO constellation (id, region_id, name, wormhole_class_id, faction_id)
VALUES ($1, $2, $3, $4, $5);"""


class Constellation(msgspec.Struct):
    """Represents an EVE Online constellation."""

    id: int
    name: str
    region_id: int | None = None
    wormhole_class_id: int | None = None
    faction_id: int | None = None
