from __future__ import annotations

from datetime import datetime
from uuid import UUID

import msgspec

# Insert a new admin
INSERT_STMT = """\
INSERT INTO instance_admin (user_id, granted_by)
VALUES ($1, $2)
ON CONFLICT (user_id) DO NOTHING
RETURNING user_id, granted_by, date_created;
"""

# Remove an admin
DELETE_STMT = """\
DELETE FROM instance_admin
WHERE user_id = $1;
"""

# Check if user is an admin
CHECK_IS_ADMIN_STMT = """\
SELECT EXISTS(SELECT 1 FROM instance_admin WHERE user_id = $1);
"""

# List all admins with character names
LIST_STMT = """\
SELECT
    ia.user_id,
    ia.granted_by,
    ia.date_created,
    u.primary_character_id as character_id,
    c.name as character_name
FROM instance_admin ia
JOIN "user" u ON u.id = ia.user_id
LEFT JOIN character c ON c.id = u.primary_character_id
ORDER BY ia.date_created;
"""


class InstanceAdmin(msgspec.Struct):
    """Instance administrator."""

    user_id: UUID
    granted_by: UUID | None = None
    date_created: datetime | None = None


class InstanceAdminWithName(msgspec.Struct):
    """Instance administrator with character name for display."""

    user_id: UUID
    granted_by: UUID | None = None
    date_created: datetime | None = None
    character_id: int | None = None
    character_name: str | None = None
