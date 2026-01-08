from __future__ import annotations

import msgspec

INSERT_STMT = """\
INSERT INTO region (id, name, description, wormhole_class_id, faction_id)
VALUES ($1, $2, $3, $4, $5);"""


class Region(msgspec.Struct):
    """Represents an EVE Online region."""

    id: int
    name: str
    description: str | None = None
    wormhole_class_id: int | None = None
    faction_id: int | None = None
