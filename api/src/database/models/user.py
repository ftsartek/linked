from __future__ import annotations

from datetime import datetime
from uuid import UUID

import msgspec


CREATE_STMT = """\
CREATE TABLE IF NOT EXISTS "user" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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

    id: UUID | None = None
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
