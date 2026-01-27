"""SQL queries for character location operations."""

from __future__ import annotations

# Get a specific character with encrypted refresh token (owned by user)
GET_CHARACTER_FOR_LOCATION = """
SELECT
    c.id,
    c.name,
    rt.token,
    COALESCE(rt.has_location_scope, FALSE) as has_location_scope
FROM character c
LEFT JOIN refresh_token rt ON rt.character_id = c.id
WHERE c.id = $1 AND c.user_id = $2;
"""

# Get system name by ID
GET_SYSTEM_NAME = """
SELECT name FROM system WHERE id = $1;
"""

# Get ship type name by ID
GET_SHIP_TYPE_NAME = """
SELECT name FROM ship_type WHERE id = $1;
"""

# Get NPC station name by ID
GET_STATION_NAME = """
SELECT name FROM npc_station WHERE id = $1;
"""
