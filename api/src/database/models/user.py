from __future__ import annotations

from datetime import datetime
from uuid import UUID

import msgspec

from utils.datetime import ensure_utc

CREATE_STMT = """\
CREATE TABLE IF NOT EXISTS "user" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date_created TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    date_updated TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_date_created ON "user"(date_created);
"""

INSERT_STMT = """\
INSERT INTO "user" DEFAULT VALUES
RETURNING id, date_created, date_updated;
"""


class User(msgspec.Struct):
    """Represents a platform user (not an EVE character)."""

    id: UUID | None = None
    date_created: datetime | None = None
    date_updated: datetime | None = None

    @classmethod
    def from_row(cls, row: tuple) -> User:
        """Create a User from a database row."""
        return cls(
            id=row[0],
            date_created=ensure_utc(row[1]),
            date_updated=ensure_utc(row[2]),
        )
