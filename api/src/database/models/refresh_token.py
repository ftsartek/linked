from __future__ import annotations

from datetime import datetime

import msgspec


CREATE_STMT = """\
CREATE TABLE IF NOT EXISTS refresh_token (
    id SERIAL PRIMARY KEY,
    character_id BIGINT NOT NULL REFERENCES character(id) ON DELETE CASCADE,
    encrypted_token BYTEA NOT NULL,
    scopes TEXT[] NOT NULL DEFAULT '{}',
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(character_id)
);

CREATE INDEX IF NOT EXISTS idx_refresh_token_character_id ON refresh_token(character_id);
"""

UPSERT_STMT = """\
INSERT INTO refresh_token (character_id, encrypted_token, scopes, expires_at)
VALUES ($1, $2, $3, $4)
ON CONFLICT (character_id) DO UPDATE SET
    encrypted_token = EXCLUDED.encrypted_token,
    scopes = EXCLUDED.scopes,
    expires_at = EXCLUDED.expires_at,
    updated_at = NOW()
RETURNING id, character_id, encrypted_token, scopes, expires_at, created_at, updated_at;
"""

SELECT_BY_CHARACTER_STMT = """\
SELECT id, character_id, encrypted_token, scopes, expires_at, created_at, updated_at
FROM refresh_token
WHERE character_id = $1;
"""

DELETE_BY_CHARACTER_STMT = """\
DELETE FROM refresh_token WHERE character_id = $1;
"""


class RefreshToken(msgspec.Struct):
    """Represents an encrypted EVE SSO refresh token for a character."""

    id: int | None = None
    character_id: int | None = None
    encrypted_token: bytes | None = None
    scopes: list[str] | None = None
    expires_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_row(cls, row: tuple) -> RefreshToken:
        """Create a RefreshToken from a database row."""
        return cls(
            id=row[0],
            character_id=row[1],
            encrypted_token=row[2],
            scopes=row[3] if row[3] else [],
            expires_at=row[4],
            created_at=row[5],
            updated_at=row[6],
        )
