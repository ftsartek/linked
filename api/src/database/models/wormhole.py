from __future__ import annotations

import msgspec

CREATE_STMT = """
CREATE TABLE IF NOT EXISTS wormhole (
    id SERIAL PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    eve_type_id INTEGER,
    sources TEXT[],
    destination TEXT,
    mass_total BIGINT,
    mass_jump_max BIGINT,
    mass_regen BIGINT,
    lifetime INTEGER,
    is_static BOOLEAN
);

CREATE INDEX IF NOT EXISTS idx_wormhole_sources ON wormhole(sources);
CREATE INDEX IF NOT EXISTS idx_wormhole_destination ON wormhole(destination);
CREATE INDEX IF NOT EXISTS idx_wormhole_is_static ON wormhole(is_static);
CREATE INDEX IF NOT EXISTS idx_wormhole_code_trgm ON wormhole USING GIN (code gin_trgm_ops);
"""

INSERT_STMT = """
INSERT INTO wormhole
    (code, eve_type_id, sources, destination, mass_total, mass_jump_max, mass_regen, lifetime, is_static)
VALUES
    ($1, $2, $3, $4, $5, $6, $7, $8, $9)
RETURNING id;"""


class Wormhole(msgspec.Struct):
    """Represents a wormhole type (e.g., K162, C140, N944)."""

    code: str
    sources: list[str]
    destination: str
    eve_type_id: int | None = None
    mass_total: int | None = None
    mass_jump_max: int | None = None
    mass_regen: int | None = None
    lifetime: int | None = None
    is_static: bool | None = None
    id: int | None = None

    @classmethod
    def from_wormhole_data(cls, code: str, data: dict) -> Wormhole:
        """Create a Wormhole from wormholes.yaml data."""
        return cls(
            code=code,
            sources=data["sources"],
            destination=data["destination"],
            eve_type_id=data.get("typeID"),
            mass_total=data.get("mass_total"),
            mass_jump_max=data.get("mass_jump_max"),
            mass_regen=data.get("mass_regen"),
            lifetime=data.get("lifetime"),
            is_static=data.get("static"),
        )
