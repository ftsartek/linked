"""SQL queries for map operations."""

from __future__ import annotations

LIST_OWNED_MAPS = """
SELECT id, owner_id, name, description, is_public, date_created, date_updated
FROM map
WHERE owner_id = $1
ORDER BY date_updated DESC;
"""

LIST_SHARED_MAPS = """
SELECT m.id, m.owner_id, m.name, m.description, m.is_public, m.date_created, m.date_updated
FROM map m
JOIN map_user mu ON m.id = mu.map_id
WHERE mu.user_id = $1
ORDER BY m.date_updated DESC;
"""

LIST_CORPORATION_MAPS = """
SELECT m.id, m.owner_id, m.name, m.description, m.is_public, m.date_created, m.date_updated
FROM map m
JOIN map_corporation mc ON m.id = mc.map_id
WHERE mc.corporation_id = $1
ORDER BY m.date_updated DESC;
"""

LIST_ALLIANCE_MAPS = """
SELECT m.id, m.owner_id, m.name, m.description, m.is_public, m.date_created, m.date_updated
FROM map m
JOIN map_alliance ma ON m.id = ma.map_id
WHERE ma.alliance_id = $1
ORDER BY m.date_updated DESC;
"""

GET_MAP = """
SELECT id, owner_id, name, description, is_public, date_created, date_updated
FROM map
WHERE id = $1;
"""

GET_MAP_NODES = """
SELECT
    n.id, n.pos_x, n.pos_y,
    s.id AS system_id, s.name AS system_name,
    c.id AS constellation_id, c.name AS constellation_name,
    r.id AS region_id, r.name AS region_name,
    s.security_status, s.security_class, s.wh_class,
    e.name AS wh_effect_name, e.raw_buffs AS raw_buffs, e.raw_debuffs AS raw_debuffs
FROM node n
JOIN system s ON n.system_id = s.id
LEFT JOIN constellation c ON s.constellation_id = c.id
LEFT JOIN region r ON c.region_id = r.id
LEFT JOIN effect e ON s.wh_effect_id = e.id
WHERE n.map_id = $1
ORDER BY n.id;
"""

GET_MAP_LINKS = """
SELECT
    l.id, l.source_node_id, l.target_node_id,
    w.code AS wormhole_code,
    w.mass_total AS wormhole_mass_total,
    w.mass_jump_max AS wormhole_mass_jump_max,
    w.mass_regen AS wormhole_mass_regen,
    w.lifetime AS wormhole_lifetime,
    w.is_static AS wormhole_is_static,
    l.lifetime_status, l.date_lifetime_updated,
    l.mass_usage, l.date_mass_updated
FROM link l
LEFT JOIN wormhole w ON l.wormhole_id = w.id
WHERE l.map_id = $1
ORDER BY l.id;
"""

CHECK_ACCESS = """
SELECT EXISTS(
    SELECT 1 FROM map WHERE id = $1 AND (owner_id = $2 OR is_public = true)
    UNION
    SELECT 1 FROM map_user WHERE map_id = $1 AND user_id = $2
    UNION
    SELECT 1 FROM map_corporation WHERE map_id = $1 AND corporation_id = $3
    UNION
    SELECT 1 FROM map_alliance WHERE map_id = $1 AND alliance_id = $4
);
"""

GET_USER_CHARACTER = """
SELECT corporation_id, alliance_id
FROM character
WHERE user_id = $1
LIMIT 1;
"""

UPDATE_MAP = """
UPDATE map
SET name = COALESCE($2, name),
    description = COALESCE($3, description),
    is_public = COALESCE($4, is_public),
    date_updated = NOW()
WHERE id = $1
RETURNING id, owner_id, name, description, is_public, date_created, date_updated;
"""

DELETE_MAP = """
DELETE FROM map WHERE id = $1;
"""
