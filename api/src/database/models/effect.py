from __future__ import annotations

import msgspec


CREATE_STMT = """\
CREATE TABLE IF NOT EXISTS effect (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    buffs JSONB,
    debuffs JSONB
);"""

INSERT_STMT = """\
INSERT INTO effect (name, buffs, debuffs)
VALUES ($1, $2, $3)
RETURNING id;"""


class Effect(msgspec.Struct):
    """Represents a wormhole space effect (e.g., Magnetar, Wolf-Rayet)."""

    name: str
    buffs: list[dict] | None = None
    debuffs: list[dict] | None = None
    id: int | None = None

    @classmethod
    def from_effect_data(cls, name: str, data: dict) -> Effect:
        """Create an Effect from effects.yaml data."""
        return cls(
            name=name,
            buffs=data.get("buffs"),
            debuffs=data.get("debuffs"),
        )
