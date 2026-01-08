from __future__ import annotations

from datetime import datetime
from uuid import UUID

import msgspec

INSERT_STMT = """\
INSERT INTO map_subscription (map_id, user_id)
VALUES ($1, $2)
ON CONFLICT (map_id, user_id) DO NOTHING;
"""

DELETE_STMT = """\
DELETE FROM map_subscription
WHERE map_id = $1 AND user_id = $2;
"""


class MapSubscription(msgspec.Struct):
    """Join table linking users to public maps they've subscribed to."""

    map_id: UUID
    user_id: UUID
    date_created: datetime | None = None
