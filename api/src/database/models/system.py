from __future__ import annotations

import msgspec

CREATE_STMT = """\
CREATE TABLE IF NOT EXISTS system (
    id INTEGER PRIMARY KEY,
    constellation_id INTEGER REFERENCES constellation(id),
    name TEXT NOT NULL,
    security_status REAL,
    security_class TEXT,
    system_class INTEGER,
    faction_id INTEGER,
    star_id INTEGER,
    radius REAL,
    pos_x REAL,
    pos_y REAL,
    stargate_ids INTEGER[],
    wh_effect_id INTEGER REFERENCES effect(id)
);

CREATE INDEX IF NOT EXISTS idx_system_constellation_id ON system(constellation_id);
CREATE INDEX IF NOT EXISTS idx_system_name ON system(name);
CREATE INDEX IF NOT EXISTS idx_system_name_trgm ON system USING GIN (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_system_system_class ON system(system_class);
CREATE INDEX IF NOT EXISTS idx_system_wh_effect_id ON system(wh_effect_id);
"""

INSERT_STMT = """\
INSERT INTO system
    (id, constellation_id, name, security_status, security_class,
     system_class, faction_id, star_id, radius, pos_x, pos_y, stargate_ids, wh_effect_id)
VALUES
    ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13);"""


class System(msgspec.Struct):
    """Represents an EVE Online solar system (K-space or J-space)."""

    id: int
    name: str
    constellation_id: int | None = None
    security_status: float | None = None
    security_class: str | None = None
    system_class: int | None = None
    faction_id: int | None = None
    star_id: int | None = None
    radius: float | None = None
    pos_x: float | None = None
    pos_y: float | None = None
    stargate_ids: list[int] | None = None
    wh_effect_id: int | None = None

    @property
    def is_wormhole(self) -> bool:
        """Check if this system is a wormhole (J-space)."""
        return self.system_class is not None and self.system_class <= 18

    @property
    def is_unidentified(self) -> bool:
        """Check if this is an unidentified placeholder system."""
        return self.id < 0
