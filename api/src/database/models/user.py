from __future__ import annotations

from datetime import datetime
from uuid import UUID

import msgspec

# Note: FK constraint added via ALTER after character table exists
ADD_PRIMARY_CHARACTER_FK = """\
ALTER TABLE "user" ADD CONSTRAINT fk_user_primary_character
    FOREIGN KEY (primary_character_id) REFERENCES character(id) ON DELETE SET NULL;
"""

INSERT_STMT = """\
INSERT INTO "user" DEFAULT VALUES
RETURNING id, date_created, date_updated;
"""


class User(msgspec.Struct):
    """Represents a platform user (not an EVE character)."""

    id: UUID | None = None
    primary_character_id: int | None = None
    date_created: datetime | None = None
    date_updated: datetime | None = None
