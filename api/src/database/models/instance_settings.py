from __future__ import annotations

from datetime import datetime
from uuid import UUID

import msgspec

# Get the current instance settings (singleton)
SELECT_STMT = """\
SELECT owner_id, is_open, date_created, date_updated
FROM instance_settings
WHERE id = 1;
"""

# Initialize instance settings with the first owner
INSERT_STMT = """\
INSERT INTO instance_settings (owner_id, is_open)
VALUES ($1, FALSE)
ON CONFLICT (id) DO NOTHING
RETURNING owner_id, is_open, date_created, date_updated;
"""

# Update is_open setting
UPDATE_IS_OPEN_STMT = """\
UPDATE instance_settings
SET is_open = $1, date_updated = NOW()
WHERE id = 1
RETURNING owner_id, is_open, date_created, date_updated;
"""

# Transfer ownership to a new user
UPDATE_OWNER_STMT = """\
UPDATE instance_settings
SET owner_id = $1, date_updated = NOW()
WHERE id = 1
RETURNING owner_id, is_open, date_created, date_updated;
"""

# Check if instance has an owner (for first-user detection)
CHECK_HAS_OWNER_STMT = """\
SELECT EXISTS(SELECT 1 FROM instance_settings WHERE id = 1);
"""

# Check if user is the owner
CHECK_IS_OWNER_STMT = """\
SELECT EXISTS(SELECT 1 FROM instance_settings WHERE id = 1 AND owner_id = $1);
"""


class InstanceSettings(msgspec.Struct):
    """Instance-wide settings including owner."""

    owner_id: UUID
    is_open: bool = False
    date_created: datetime | None = None
    date_updated: datetime | None = None
