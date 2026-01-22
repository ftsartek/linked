"""Default map subscription model for auto-subscribing new users."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

import msgspec

# List all default subscriptions with map details
LIST_STMT = """\
SELECT
    d.map_id,
    m.name AS map_name,
    d.added_by,
    d.date_created
FROM default_map_subscription d
JOIN map m ON m.id = d.map_id AND m.date_deleted IS NULL
ORDER BY d.date_created;
"""

# Get just the map IDs for signup flow
GET_MAP_IDS_STMT = """\
SELECT d.map_id
FROM default_map_subscription d
JOIN map m ON m.id = d.map_id AND m.date_deleted IS NULL AND m.is_public = TRUE;
"""

# Add a map to default subscriptions
INSERT_STMT = """\
INSERT INTO default_map_subscription (map_id, added_by)
VALUES ($1, $2)
ON CONFLICT (map_id) DO NOTHING
RETURNING map_id, added_by, date_created;
"""

# Remove a map from default subscriptions
DELETE_STMT = """\
DELETE FROM default_map_subscription
WHERE map_id = $1
RETURNING map_id;
"""

# Check if a map is a default subscription
CHECK_STMT = """\
SELECT EXISTS(SELECT 1 FROM default_map_subscription WHERE map_id = $1);
"""


class DefaultMapSubscription(msgspec.Struct):
    """Default map subscription entry."""

    map_id: UUID
    added_by: UUID | None = None
    date_created: datetime | None = None


class DefaultMapSubscriptionWithName(msgspec.Struct):
    """Default map subscription entry with map name for display."""

    map_id: UUID
    map_name: str
    added_by: UUID | None = None
    date_created: datetime | None = None
