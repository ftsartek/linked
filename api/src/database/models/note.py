from __future__ import annotations

from datetime import datetime
from uuid import UUID

import msgspec

INSERT_STMT = """\
INSERT INTO note (solar_system_id, map_id, title, content, created_by, date_expires)
VALUES ($1, $2, $3, $4, $5, $6)
RETURNING id, solar_system_id, map_id, title, content, created_by, updated_by, date_expires, date_created, date_updated;
"""

UPDATE_STMT = """\
UPDATE note
SET title = COALESCE($2, title),
    content = COALESCE($3, content),
    date_expires = $4,
    updated_by = $5,
    date_updated = NOW()
WHERE id = $1 AND date_deleted IS NULL
RETURNING id, solar_system_id, map_id, title, content, created_by, updated_by, date_expires, date_created, date_updated;
"""


class Note(msgspec.Struct):
    """Represents a note on a solar system within a map."""

    solar_system_id: int
    map_id: UUID
    content: str
    created_by: int  # character_id
    title: str | None = None
    updated_by: int | None = None
    date_expires: datetime | None = None
    id: UUID | None = None
    date_created: datetime | None = None
    date_updated: datetime | None = None
    date_deleted: datetime | None = None
