from __future__ import annotations

from datetime import datetime

import msgspec


CREATE_STMT = """\
CREATE TABLE IF NOT EXISTS "user" (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_created_at ON "user"(created_at);
"""

INSERT_STMT = """\
INSERT INTO "user" DEFAULT VALUES
RETURNING id, created_at, updated_at;
"""


class User(msgspec.Struct):
    """Represents a platform user (not an EVE character)."""

    id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_row(cls, row: tuple) -> User:
        """Create a User from a database row."""
        return cls(
            id=row[0],
            created_at=row[1],
            updated_at=row[2],
        )
