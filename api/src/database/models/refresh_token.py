from __future__ import annotations

from datetime import datetime
from uuid import UUID

import msgspec

CREATE_STMT = """
CREATE TABLE IF NOT EXISTS refresh_token (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    character_id BIGINT NOT NULL REFERENCES character(id) ON DELETE CASCADE,
    token BYTEA NOT NULL,
    scopes TEXT[] NOT NULL DEFAULT '{}',
    expires_at TIMESTAMPTZ,
    date_created TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    date_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(character_id)
);

CREATE INDEX IF NOT EXISTS idx_refresh_token_character_id ON refresh_token(character_id);
"""

UPSERT_STMT = """
INSERT INTO refresh_token (character_id, token, scopes, expires_at)
VALUES ($1, $2, $3, $4)
ON CONFLICT (character_id) DO UPDATE SET
    token = EXCLUDED.token,
    scopes = EXCLUDED.scopes,
    expires_at = EXCLUDED.expires_at,
    date_updated = NOW()
RETURNING id, character_id, token, scopes, expires_at, date_created, date_updated;
"""

SELECT_BY_CHARACTER_STMT = """
SELECT id, character_id, token, scopes, expires_at, date_created, date_updated
FROM refresh_token
WHERE character_id = $1;
"""

DELETE_BY_CHARACTER_STMT = """
DELETE FROM refresh_token WHERE character_id = $1;
"""


class RefreshToken(msgspec.Struct):
    """Represents an encrypted EVE SSO refresh token for a character."""

    id: UUID | None = None
    character_id: int | None = None
    token: bytes | None = None
    scopes: list[str] | None = None
    expires_at: datetime | None = None
    date_created: datetime | None = None
    date_updated: datetime | None = None
