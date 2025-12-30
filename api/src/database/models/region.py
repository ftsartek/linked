from __future__ import annotations

import msgspec

CREATE_STMT = """\
CREATE TABLE IF NOT EXISTS region (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    wormhole_class_id INTEGER,
    faction_id INTEGER
);

CREATE INDEX IF NOT EXISTS idx_region_name ON region(name);
"""

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
