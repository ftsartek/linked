"""SQL queries for character location operations."""

from __future__ import annotations

# Get a specific character with encrypted refresh token (owned by user)
GET_CHARACTER_FOR_LOCATION = """
SELECT
    c.id,
    c.name,
    rt.token,
    COALESCE(rt.has_location_scope, FALSE) as has_location_scope,
    corp.name AS corporation_name,
    alliance.name AS alliance_name
FROM character c
LEFT JOIN refresh_token rt ON rt.character_id = c.id
LEFT JOIN corporation corp ON corp.id = c.corporation_id
LEFT JOIN alliance ON alliance.id = c.alliance_id
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

# Update refresh token after rotation (preserves scopes and other metadata)
UPDATE_REFRESH_TOKEN = """
UPDATE refresh_token
SET token = $2, date_updated = NOW()
WHERE character_id = $1;
"""

# Delete refresh token when revoked
DELETE_REFRESH_TOKEN = """
DELETE FROM refresh_token WHERE character_id = $1;
"""
