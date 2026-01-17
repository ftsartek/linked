from __future__ import annotations

from datetime import datetime

import msgspec

from utils.enums import RouteType

SELECT_STMT = """
SELECT id, origin_system_id, destination_system_id, route_type, waypoints, jump_count,
       date_created, date_updated
FROM esi_route_cache
WHERE origin_system_id = $1 AND destination_system_id = $2 AND route_type = $3;
"""

INSERT_STMT = """
INSERT INTO esi_route_cache (origin_system_id, destination_system_id, route_type, waypoints, jump_count)
VALUES ($1, $2, $3, $4, $5)
ON CONFLICT (origin_system_id, destination_system_id, route_type)
DO UPDATE SET waypoints = EXCLUDED.waypoints, jump_count = EXCLUDED.jump_count, date_updated = NOW()
RETURNING id, origin_system_id, destination_system_id, route_type, waypoints, jump_count,
          date_created, date_updated;
"""


class ESIRouteCache(msgspec.Struct):
    """Cached ESI route between two k-space systems."""

    origin_system_id: int
    destination_system_id: int
    route_type: RouteType
    waypoints: list[int]  # System IDs in order (includes origin and destination)
    jump_count: int
    id: int | None = None
    date_created: datetime | None = None
    date_updated: datetime | None = None
