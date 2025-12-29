from __future__ import annotations

import msgspec

CREATE_STMT = """\
CREATE TABLE IF NOT EXISTS system (
    id INTEGER PRIMARY KEY,
    constellation_id INTEGER REFERENCES constellation(id),
    name TEXT NOT NULL,
    security_status REAL NOT NULL,
    system_class TEXT NOT NULL,
    alt_class TEXT,
    star_id INTEGER,
    wh_effect_id INTEGER REFERENCES effect(id)
);

CREATE INDEX IF NOT EXISTS idx_system_constellation_id ON system(constellation_id);
CREATE INDEX IF NOT EXISTS idx_system_name ON system(name);
CREATE INDEX IF NOT EXISTS idx_system_name_trgm ON system USING GIN (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_system_wh_class ON system(wh_class);
CREATE INDEX IF NOT EXISTS idx_system_wh_effect_id ON system(wh_effect_id);
"""

INSERT_STMT = """\
INSERT INTO system (id, constellation_id, name, security_status, security_class, star_id, wh_class, wh_effect_id)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8);"""


class System(msgspec.Struct):
    """Represents an EVE Online solar system (K-space or J-space)."""

    id: int
    name: str
    system_class: str
    security_status: float
    alt_class: str | None = None
    constellation_id: int | None = None
    star_id: int | None = None
    wh_effect_id: int | None = None

    @classmethod
    def from_system_data(
        cls,
        data: dict,
        wh_data: dict | None = None,
        wh_effect_id: int | None = None,
    ) -> System:
        """
        Create a System from systems.yaml data, optionally merging wormhole data.

        Args:
            data: Entry from systems.yaml
            wh_data: Entry from wormhole_systems.yaml (if this is a J-space system)
            wh_effect_id: Database ID of the effect (looked up from wh_data["effect"])
        """
        system = cls(
            id=data["system_id"],
            name=data["name"],
            constellation_id=data.get("constellation_id"),
            security_status=data.get("security_status"),
            security_class=data.get("security_class"),
            star_id=data.get("star_id"),
        )

        if wh_data is not None:
            system = msgspec.structs.replace(
                system,
                wh_class=wh_data.get("class"),
                wh_effect_id=wh_effect_id,
            )

        return system

    @property
    def is_wormhole(self) -> bool:
        """Check if this system is a wormhole (J-space)."""
        return self.wh_class is not None
