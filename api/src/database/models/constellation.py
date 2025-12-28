from __future__ import annotations

import msgspec

CREATE_STMT = """
CREATE TABLE IF NOT EXISTS constellation (
    id INTEGER PRIMARY KEY,
    region_id INTEGER REFERENCES region(id),
    name TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_constellation_region_id ON constellation(region_id);
CREATE INDEX IF NOT EXISTS idx_constellation_name ON constellation(name);
"""

INSERT_STMT = """
INSERT INTO constellation (id, region_id, name)
VALUES ($1, $2, $3);"""


class Constellation(msgspec.Struct):
    """Represents an EVE Online constellation."""

    id: int
    name: str
    region_id: int | None = None

    @classmethod
    def from_constellation_data(cls, data: dict) -> Constellation:
        """Create a Constellation from constellations.yaml data."""
        return cls(
            id=data["constellation_id"],
            name=data["name"],
            region_id=data.get("region_id"),
        )
