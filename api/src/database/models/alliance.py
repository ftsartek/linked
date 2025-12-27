from __future__ import annotations

from datetime import datetime

import msgspec


CREATE_STMT = """\
CREATE TABLE IF NOT EXISTS alliance (
    id BIGINT PRIMARY KEY,
    name TEXT NOT NULL,
    ticker TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alliance_name ON alliance(name);
CREATE INDEX IF NOT EXISTS idx_alliance_ticker ON alliance(ticker);
"""

INSERT_STMT = """\
INSERT INTO alliance (id, name, ticker)
VALUES ($1, $2, $3)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    ticker = EXCLUDED.ticker,
    updated_at = NOW()
RETURNING id, name, ticker, created_at, updated_at;
"""


class Alliance(msgspec.Struct):
    """Represents an EVE Online alliance."""

    id: int  # EVE alliance_id
    name: str
    ticker: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_esi_data(cls, alliance_id: int, data: dict) -> Alliance:
        """Create an Alliance from ESI alliance data."""
        return cls(
            id=alliance_id,
            name=data["name"],
            ticker=data["ticker"],
        )

    @classmethod
    def from_row(cls, row: tuple) -> Alliance:
        """Create an Alliance from a database row."""
        return cls(
            id=row[0],
            name=row[1],
            ticker=row[2],
            created_at=row[3],
            updated_at=row[4],
        )
