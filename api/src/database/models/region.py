from __future__ import annotations

import msgspec

CREATE_STMT = """\
CREATE TABLE IF NOT EXISTS region (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT
);

CREATE INDEX IF NOT EXISTS idx_region_name ON region(name);
"""

INSERT_STMT = """\
INSERT INTO region (id, name, description)
VALUES ($1, $2, $3);"""


class Region(msgspec.Struct):
    """Represents an EVE Online region."""

    id: int
    name: str
    description: str | None = None

    @classmethod
    def from_region_data(cls, data: dict) -> Region:
        """Create a Region from regions.yaml data."""
        return cls(
            id=data["region_id"],
            name=data["name"],
            description=data.get("description"),
        )
