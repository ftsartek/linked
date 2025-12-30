from __future__ import annotations

import msgspec

CREATE_STMT = """
CREATE TABLE IF NOT EXISTS wormhole (
    id SERIAL PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    eve_type_id INTEGER,
    sources INTEGER[],
    target_class INTEGER,
    mass_total BIGINT,
    mass_jump_max BIGINT,
    mass_regen BIGINT,
    lifetime REAL,
    target_regions INTEGER[],
    target_constellations INTEGER[],
    target_systems INTEGER[]
);

CREATE INDEX IF NOT EXISTS idx_wormhole_sources ON wormhole USING GIN (sources);
CREATE INDEX IF NOT EXISTS idx_wormhole_target_class ON wormhole(target_class);
CREATE INDEX IF NOT EXISTS idx_wormhole_code_trgm ON wormhole USING GIN (code gin_trgm_ops);
"""

INSERT_STMT = """
INSERT INTO wormhole
    (code, eve_type_id, sources, target_class, mass_total, mass_jump_max, mass_regen,
     lifetime, target_regions, target_constellations, target_systems)
VALUES
    ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
RETURNING id;"""


class Wormhole(msgspec.Struct):
    """Represents a wormhole type (e.g., K162, C140, N944)."""

    code: str
    sources: list[int] | None = None
    target_class: int | None = None
    eve_type_id: int | None = None
    mass_total: int | None = None
    mass_jump_max: int | None = None
    mass_regen: int | None = None
    lifetime: float | None = None
    target_regions: list[int] | None = None
    target_constellations: list[int] | None = None
    target_systems: list[int] | None = None
    id: int | None = None
