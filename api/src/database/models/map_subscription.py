from __future__ import annotations

from datetime import datetime
from uuid import UUID

import msgspec

CREATE_STMT = """\
CREATE TABLE IF NOT EXISTS map_subscription (
    map_id UUID NOT NULL REFERENCES map(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    date_created TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (map_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_map_subscription_user_id ON map_subscription(user_id);
CREATE INDEX IF NOT EXISTS idx_map_subscription_map_id ON map_subscription(map_id);
"""

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
