from __future__ import annotations

import msgspec

CREATE_STMT = """
CREATE TABLE IF NOT EXISTS constellation (
    id INTEGER PRIMARY KEY,
    region_id INTEGER REFERENCES region(id),
    name TEXT NOT NULL,
    wormhole_class_id INTEGER,
    faction_id INTEGER
);

CREATE INDEX IF NOT EXISTS idx_constellation_region_id ON constellation(region_id);
CREATE INDEX IF NOT EXISTS idx_constellation_name ON constellation(name);
"""

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
