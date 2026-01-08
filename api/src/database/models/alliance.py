from __future__ import annotations

from datetime import datetime

import msgspec

INSERT_STMT = """\
INSERT INTO alliance (id, name, ticker)
VALUES ($1, $2, $3)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    ticker = EXCLUDED.ticker,
    date_updated = NOW()
RETURNING id, name, ticker, date_created, date_updated;
"""


class Alliance(msgspec.Struct):
    """Represents an EVE Online alliance."""

    id: int  # EVE alliance_id
    name: str
    ticker: str
    date_created: datetime | None = None
    date_updated: datetime | None = None

    @classmethod
    def from_esi_data(cls, alliance_id: int, data: dict) -> Alliance:
        """Create an Alliance from ESI alliance data."""
        return cls(
            id=alliance_id,
            name=data["name"],
            ticker=data["ticker"],
        )
