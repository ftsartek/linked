from __future__ import annotations

from datetime import datetime
from uuid import UUID

import msgspec

UPSERT_STMT = """
INSERT INTO refresh_token (character_id, token, scopes, expires_at, has_location_scope)
VALUES ($1, $2, $3, $4, $5)
ON CONFLICT (character_id) DO UPDATE SET
    token = EXCLUDED.token,
    scopes = EXCLUDED.scopes,
    expires_at = EXCLUDED.expires_at,
    has_location_scope = EXCLUDED.has_location_scope,
    date_updated = NOW()
RETURNING id, character_id, token, scopes, expires_at, has_location_scope, date_created, date_updated;
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
    has_location_scope: bool = False
    date_created: datetime | None = None
    date_updated: datetime | None = None
