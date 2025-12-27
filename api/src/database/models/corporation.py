from __future__ import annotations

from datetime import datetime

import msgspec


CREATE_STMT = """\
CREATE TABLE IF NOT EXISTS corporation (
    id BIGINT PRIMARY KEY,
    name TEXT NOT NULL,
    ticker TEXT NOT NULL,
    alliance_id BIGINT,
    member_count INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_corporation_alliance_id ON corporation(alliance_id);
CREATE INDEX IF NOT EXISTS idx_corporation_name ON corporation(name);
CREATE INDEX IF NOT EXISTS idx_corporation_ticker ON corporation(ticker);
"""

INSERT_STMT = """\
INSERT INTO corporation (id, name, ticker, alliance_id, member_count)
VALUES ($1, $2, $3, $4, $5)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    ticker = EXCLUDED.ticker,
    alliance_id = EXCLUDED.alliance_id,
    member_count = EXCLUDED.member_count,
    updated_at = NOW()
RETURNING id, name, ticker, alliance_id, member_count, created_at, updated_at;
"""


class Corporation(msgspec.Struct):
    """Represents an EVE Online corporation."""

    id: int  # EVE corporation_id
    name: str
    ticker: str
    alliance_id: int | None = None
    member_count: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_esi_data(cls, corporation_id: int, data: dict) -> Corporation:
        """Create a Corporation from ESI corporation data."""
        return cls(
            id=corporation_id,
            name=data["name"],
            ticker=data["ticker"],
            alliance_id=data.get("alliance_id"),
            member_count=data.get("member_count"),
        )

    @classmethod
    def from_row(cls, row: tuple) -> Corporation:
        """Create a Corporation from a database row."""
        return cls(
            id=row[0],
            name=row[1],
            ticker=row[2],
            alliance_id=row[3],
            member_count=row[4],
            created_at=row[5],
            updated_at=row[6],
        )
