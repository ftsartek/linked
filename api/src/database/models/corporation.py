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
    date_created TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    date_updated TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_corporation_alliance_id ON corporation(alliance_id);
CREATE INDEX IF NOT EXISTS idx_corporation_name ON corporation(name);
CREATE INDEX IF NOT EXISTS idx_corporation_ticker ON corporation(ticker);
CREATE INDEX IF NOT EXISTS idx_corporation_name_trgm ON corporation USING GIN (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_corporation_ticker_trgm ON corporation USING GIN (ticker gin_trgm_ops);
"""

INSERT_STMT = """\
INSERT INTO corporation (id, name, ticker, alliance_id, member_count)
VALUES ($1, $2, $3, $4, $5)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    ticker = EXCLUDED.ticker,
    alliance_id = EXCLUDED.alliance_id,
    member_count = EXCLUDED.member_count,
    date_updated = NOW()
RETURNING id, name, ticker, alliance_id, member_count, date_created, date_updated;
"""


class Corporation(msgspec.Struct):
    """Represents an EVE Online corporation."""

    id: int  # EVE corporation_id
    name: str
    ticker: str
    alliance_id: int | None = None
    member_count: int | None = None
    date_created: datetime | None = None
    date_updated: datetime | None = None

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
