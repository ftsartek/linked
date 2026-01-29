"""SQL queries for map operations."""

from __future__ import annotations

LIST_OWNED_MAPS = """
SELECT
    id, owner_id, name, description, is_public, public_read_only, edge_type,
    rankdir, auto_layout, node_sep, rank_sep, location_tracking_enabled,
    date_created, date_updated, true AS edit_access
FROM map
WHERE owner_id = $1
ORDER BY date_updated DESC;
"""

LIST_CHARACTER_SHARED_MAPS = """
SELECT DISTINCT m.id, m.owner_id, m.name, m.description, m.is_public, m.public_read_only,
    m.edge_type, m.rankdir, m.auto_layout, m.node_sep, m.rank_sep, m.location_tracking_enabled,
    m.date_created, m.date_updated,
    CASE
        WHEN m.owner_id = $1 THEN true
        ELSE NOT mch.read_only
    END AS edit_access
FROM map m
JOIN map_character mch ON m.id = mch.map_id
JOIN character c ON mch.character_id = c.id
WHERE c.user_id = $1
ORDER BY m.date_updated DESC;
"""

LIST_CORPORATION_MAPS = """
SELECT m.id, m.owner_id, m.name, m.description, m.is_public, m.public_read_only, m.edge_type,
    m.rankdir, m.auto_layout, m.node_sep, m.rank_sep, m.location_tracking_enabled,
    m.date_created, m.date_updated,
    CASE
        WHEN m.owner_id = $2 THEN true
        WHEN mch.map_id IS NOT NULL THEN NOT mch.read_only
        ELSE NOT mc.read_only
    END AS edit_access
FROM map m
JOIN map_corporation mc ON m.id = mc.map_id
LEFT JOIN map_character mch ON m.id = mch.map_id
    AND mch.character_id IN (SELECT id FROM character WHERE user_id = $2)
WHERE mc.corporation_id = $1
ORDER BY m.date_updated DESC;
"""

LIST_ALLIANCE_MAPS = """
SELECT m.id, m.owner_id, m.name, m.description, m.is_public, m.public_read_only, m.edge_type,
    m.rankdir, m.auto_layout, m.node_sep, m.rank_sep, m.location_tracking_enabled,
    m.date_created, m.date_updated,
    CASE
        WHEN m.owner_id = $2 THEN true
        WHEN mch.map_id IS NOT NULL THEN NOT mch.read_only
        WHEN mc.map_id IS NOT NULL THEN NOT mc.read_only
        ELSE NOT ma.read_only
    END AS edit_access
FROM map m
JOIN map_alliance ma ON m.id = ma.map_id
LEFT JOIN map_character mch ON m.id = mch.map_id
    AND mch.character_id IN (SELECT id FROM character WHERE user_id = $2)
LEFT JOIN map_corporation mc ON m.id = mc.map_id AND mc.corporation_id = $3
WHERE ma.alliance_id = $1
ORDER BY m.date_updated DESC;
"""

GET_MAP = """
SELECT
    id, owner_id, name, description, is_public, public_read_only, edge_type,
    rankdir, auto_layout, node_sep, rank_sep, location_tracking_enabled,
    date_created, date_updated
FROM map
WHERE id = $1;
"""

GET_MAP_NODES = """
SELECT
    n.id, n.pos_x, n.pos_y, n.locked,
    s.id AS system_id, s.name AS system_name,
    c.id AS constellation_id, c.name AS constellation_name,
    r.id AS region_id, r.name AS region_name,
    s.security_status, s.security_class, s.system_class,
    e.name AS wh_effect_name, e.buffs AS raw_buffs, e.debuffs AS raw_debuffs,
    array_remove(array_agg(w.code), NULL) AS static_codes,
    array_remove(array_agg(w.target_class), NULL) AS static_target_classes
FROM node n
JOIN system s ON n.system_id = s.id
LEFT JOIN constellation c ON s.constellation_id = c.id
LEFT JOIN region r ON c.region_id = r.id
LEFT JOIN effect e ON s.wh_effect_id = e.id
LEFT JOIN system_static ss ON s.id = ss.system_id
LEFT JOIN wormhole w ON ss.wormhole_id = w.id
WHERE n.map_id = $1 AND n.date_deleted IS NULL
GROUP BY n.id, n.pos_x, n.pos_y, n.locked, s.id, s.name, c.id, c.name, r.id, r.name,
         s.security_status, s.security_class, s.system_class,
         e.name, e.buffs, e.debuffs
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
    l.lifetime_status, l.date_lifetime_updated,
    l.mass_usage, l.date_mass_updated
FROM link l
LEFT JOIN wormhole w ON l.wormhole_id = w.id
WHERE l.map_id = $1 AND l.date_deleted IS NULL
ORDER BY l.id;
"""

LIST_MAP_CHARACTERS = """
SELECT mc.character_id, c.name AS character_name, mc.read_only
FROM map_character mc
JOIN character c ON c.id = mc.character_id
WHERE mc.map_id = $1
ORDER BY c.name;
"""

LIST_MAP_CORPORATIONS = """
SELECT mc.corporation_id, c.name AS corporation_name, c.ticker AS corporation_ticker, mc.read_only
FROM map_corporation mc
JOIN corporation c ON c.id = mc.corporation_id
WHERE mc.map_id = $1
ORDER BY c.name;
"""

LIST_MAP_ALLIANCES = """
SELECT ma.alliance_id, a.name AS alliance_name, a.ticker AS alliance_ticker, ma.read_only
FROM map_alliance ma
JOIN alliance a ON a.id = ma.alliance_id
WHERE ma.map_id = $1
ORDER BY a.name;
"""

UPDATE_MAP = """
UPDATE map
SET name = COALESCE($2, name),
    description = COALESCE($3, description),
    is_public = COALESCE($4, is_public),
    public_read_only = COALESCE($5, public_read_only),
    edge_type = COALESCE($6, edge_type),
    rankdir = COALESCE($7, rankdir),
    auto_layout = COALESCE($8, auto_layout),
    node_sep = COALESCE($9, node_sep),
    rank_sep = COALESCE($10, rank_sep),
    location_tracking_enabled = COALESCE($11, location_tracking_enabled),
    date_updated = NOW()
WHERE id = $1
RETURNING
    id, owner_id, name, description, is_public, public_read_only, edge_type,
    rankdir, auto_layout, node_sep, rank_sep, location_tracking_enabled,
    date_created, date_updated;
"""

DELETE_MAP = """
DELETE FROM map WHERE id = $1;
"""

INSERT_NODE = """
INSERT INTO node (map_id, system_id, pos_x, pos_y)
VALUES ($1, $2, $3, $4)
RETURNING id;
"""

GET_NODE_ENRICHED = """
SELECT
    n.id, n.pos_x, n.pos_y, n.locked,
    s.id AS system_id, s.name AS system_name,
    c.id AS constellation_id, c.name AS constellation_name,
    r.id AS region_id, r.name AS region_name,
    s.security_status, s.security_class, s.system_class,
    e.name AS wh_effect_name, e.buffs AS raw_buffs, e.debuffs AS raw_debuffs,
    array_remove(array_agg(w.code), NULL) AS static_codes,
    array_remove(array_agg(w.target_class), NULL) AS static_target_classes
FROM node n
JOIN system s ON n.system_id = s.id
LEFT JOIN constellation c ON s.constellation_id = c.id
LEFT JOIN region r ON c.region_id = r.id
LEFT JOIN effect e ON s.wh_effect_id = e.id
LEFT JOIN system_static ss ON s.id = ss.system_id
LEFT JOIN wormhole w ON ss.wormhole_id = w.id
WHERE n.id = $1 AND n.date_deleted IS NULL
GROUP BY n.id, n.pos_x, n.pos_y, n.locked, s.id, s.name, c.id, c.name, r.id, r.name,
         s.security_status, s.security_class, s.system_class,
         e.name, e.buffs, e.debuffs;
"""

GET_K162_ID = """
SELECT id FROM wormhole WHERE code = 'K162' LIMIT 1;
"""

INSERT_LINK = """
INSERT INTO link (map_id, source_node_id, target_node_id, wormhole_id)
VALUES ($1, $2, $3, $4)
RETURNING id;
"""

GET_LINK_ENRICHED = """
SELECT
    l.id, l.source_node_id, l.target_node_id,
    w.code AS wormhole_code,
    w.mass_total AS wormhole_mass_total,
    w.mass_jump_max AS wormhole_mass_jump_max,
    w.mass_regen AS wormhole_mass_regen,
    w.lifetime AS wormhole_lifetime,
    l.lifetime_status, l.date_lifetime_updated,
    l.mass_usage, l.date_mass_updated
FROM link l
LEFT JOIN wormhole w ON l.wormhole_id = w.id
WHERE l.id = $1 AND l.date_deleted IS NULL;
"""

UPDATE_NODE_POSITION = """
UPDATE node
SET pos_x = $2, pos_y = $3, date_updated = NOW()
WHERE id = $1 AND map_id = $4 AND date_deleted IS NULL
RETURNING id;
"""

UPDATE_NODE_SYSTEM = """
UPDATE node
SET system_id = $2, date_updated = NOW()
WHERE id = $1 AND map_id = $3 AND date_deleted IS NULL
RETURNING id;
"""

DELETE_NODE = """
UPDATE node
SET date_deleted = NOW(), date_updated = NOW()
WHERE id = $1 AND map_id = $2 AND date_deleted IS NULL
RETURNING id;
"""

UPDATE_LINK = """
UPDATE link
SET wormhole_id = COALESCE($2, wormhole_id),
    lifetime_status = COALESCE($3, lifetime_status),
    mass_usage = COALESCE($4, mass_usage),
    date_updated = NOW()
WHERE id = $1 AND map_id = $5 AND date_deleted IS NULL
RETURNING id;
"""

DELETE_LINK = """
UPDATE link
SET date_deleted = NOW(), date_updated = NOW()
WHERE id = $1 AND map_id = $2 AND date_deleted IS NULL
RETURNING id;
"""

GET_NODE_MAP_ID = """
SELECT map_id FROM node WHERE id = $1;
"""

GET_LINK_MAP_ID = """
SELECT map_id FROM link WHERE id = $1;
"""

# Queries for fetching related IDs before soft-delete operations

GET_NODE_CONNECTED_LINK_IDS = """
SELECT id FROM link
WHERE (source_node_id = $1 OR target_node_id = $1) AND date_deleted IS NULL;
"""

SOFT_DELETE_NODE_CONNECTED_LINKS = """
UPDATE link
SET date_deleted = NOW(), date_updated = NOW()
WHERE (source_node_id = $1 OR target_node_id = $1) AND map_id = $2 AND date_deleted IS NULL
RETURNING id;
"""

GET_MAP_NODE_IDS = """
SELECT id FROM node
WHERE map_id = $1 AND date_deleted IS NULL;
"""

GET_MAP_LINK_IDS = """
SELECT id FROM link
WHERE map_id = $1 AND date_deleted IS NULL;
"""

SOFT_DELETE_MAP = """
UPDATE map
SET date_deleted = NOW(), date_updated = NOW()
WHERE id = $1 AND date_deleted IS NULL
RETURNING id;
"""

SOFT_DELETE_MAP_NODES = """
UPDATE node
SET date_deleted = NOW(), date_updated = NOW()
WHERE map_id = $1 AND date_deleted IS NULL
RETURNING id;
"""

SOFT_DELETE_MAP_LINKS = """
UPDATE link
SET date_deleted = NOW(), date_updated = NOW()
WHERE map_id = $1 AND date_deleted IS NULL
RETURNING id;
"""

# Public map subscription queries

LIST_PUBLIC_MAPS = """
SELECT
    m.id, m.owner_id, m.name, m.description, m.is_public, m.public_read_only,
    m.edge_type, m.rankdir, m.auto_layout, m.node_sep, m.rank_sep, m.location_tracking_enabled,
    m.date_created, m.date_updated,
    false AS edit_access,
    COUNT(ms.user_id)::int AS subscription_count,
    false AS is_subscribed
FROM map m
LEFT JOIN map_subscription ms ON m.id = ms.map_id
WHERE m.is_public = true
    AND m.owner_id != $1
    AND NOT EXISTS(SELECT 1 FROM map_subscription WHERE map_id = m.id AND user_id = $1)
    AND NOT EXISTS(SELECT 1 FROM map_character WHERE map_id = m.id
        AND character_id IN (SELECT id FROM character WHERE user_id = $1))
    AND NOT EXISTS(SELECT 1 FROM map_corporation WHERE map_id = m.id AND corporation_id = $2)
    AND NOT EXISTS(SELECT 1 FROM map_alliance WHERE map_id = m.id AND alliance_id = $3)
GROUP BY m.id
ORDER BY subscription_count DESC, m.date_created DESC
LIMIT $4 OFFSET $5;
"""

COUNT_PUBLIC_MAPS = """
SELECT COUNT(*) FROM map m
WHERE m.is_public = true
    AND m.owner_id != $1
    AND NOT EXISTS(SELECT 1 FROM map_subscription WHERE map_id = m.id AND user_id = $1)
    AND NOT EXISTS(SELECT 1 FROM map_character WHERE map_id = m.id
        AND character_id IN (SELECT id FROM character WHERE user_id = $1))
    AND NOT EXISTS(SELECT 1 FROM map_corporation WHERE map_id = m.id AND corporation_id = $2)
    AND NOT EXISTS(SELECT 1 FROM map_alliance WHERE map_id = m.id AND alliance_id = $3);
"""

SEARCH_PUBLIC_MAPS = """
SELECT
    m.id, m.owner_id, m.name, m.description, m.is_public, m.public_read_only,
    m.edge_type, m.rankdir, m.auto_layout, m.node_sep, m.rank_sep, m.location_tracking_enabled,
    m.date_created, m.date_updated,
    false AS edit_access,
    COUNT(ms.user_id)::int AS subscription_count,
    false AS is_subscribed
FROM map m
LEFT JOIN map_subscription ms ON m.id = ms.map_id
WHERE m.is_public = true
    AND m.owner_id != $1
    AND NOT EXISTS(SELECT 1 FROM map_subscription WHERE map_id = m.id AND user_id = $1)
    AND NOT EXISTS(SELECT 1 FROM map_character WHERE map_id = m.id
        AND character_id IN (SELECT id FROM character WHERE user_id = $1))
    AND NOT EXISTS(SELECT 1 FROM map_corporation WHERE map_id = m.id AND corporation_id = $2)
    AND NOT EXISTS(SELECT 1 FROM map_alliance WHERE map_id = m.id AND alliance_id = $3)
    AND (m.name ILIKE '%' || $4 || '%' OR m.description ILIKE '%' || $4 || '%')
GROUP BY m.id
ORDER BY subscription_count DESC, m.date_created DESC
LIMIT $5 OFFSET $6;
"""

COUNT_SEARCH_PUBLIC_MAPS = """
SELECT COUNT(*) FROM map m
WHERE m.is_public = true
    AND m.owner_id != $1
    AND NOT EXISTS(SELECT 1 FROM map_subscription WHERE map_id = m.id AND user_id = $1)
    AND NOT EXISTS(SELECT 1 FROM map_character WHERE map_id = m.id
        AND character_id IN (SELECT id FROM character WHERE user_id = $1))
    AND NOT EXISTS(SELECT 1 FROM map_corporation WHERE map_id = m.id AND corporation_id = $2)
    AND NOT EXISTS(SELECT 1 FROM map_alliance WHERE map_id = m.id AND alliance_id = $3)
    AND (m.name ILIKE '%' || $4 || '%' OR m.description ILIKE '%' || $4 || '%');
"""

# Admin versions - list ALL public maps without filtering out owned/accessible ones
LIST_ALL_PUBLIC_MAPS = """
SELECT
    m.id, m.owner_id, m.name, m.description, m.is_public, m.public_read_only,
    m.edge_type, m.rankdir, m.auto_layout, m.node_sep, m.rank_sep, m.location_tracking_enabled,
    m.date_created, m.date_updated,
    false AS edit_access,
    COUNT(ms.user_id)::int AS subscription_count,
    false AS is_subscribed
FROM map m
LEFT JOIN map_subscription ms ON m.id = ms.map_id
WHERE m.is_public = true AND m.date_deleted IS NULL
GROUP BY m.id
ORDER BY subscription_count DESC, m.date_created DESC
LIMIT $1 OFFSET $2;
"""

COUNT_ALL_PUBLIC_MAPS = """
SELECT COUNT(*) FROM map m
WHERE m.is_public = true AND m.date_deleted IS NULL;
"""

SEARCH_ALL_PUBLIC_MAPS = """
SELECT
    m.id, m.owner_id, m.name, m.description, m.is_public, m.public_read_only,
    m.edge_type, m.rankdir, m.auto_layout, m.node_sep, m.rank_sep, m.location_tracking_enabled,
    m.date_created, m.date_updated,
    false AS edit_access,
    COUNT(ms.user_id)::int AS subscription_count,
    false AS is_subscribed
FROM map m
LEFT JOIN map_subscription ms ON m.id = ms.map_id
WHERE m.is_public = true AND m.date_deleted IS NULL
    AND (m.name ILIKE '%' || $1 || '%' OR m.description ILIKE '%' || $1 || '%')
GROUP BY m.id
ORDER BY subscription_count DESC, m.date_created DESC
LIMIT $2 OFFSET $3;
"""

COUNT_SEARCH_ALL_PUBLIC_MAPS = """
SELECT COUNT(*) FROM map m
WHERE m.is_public = true AND m.date_deleted IS NULL
    AND (m.name ILIKE '%' || $1 || '%' OR m.description ILIKE '%' || $1 || '%');
"""

LIST_SUBSCRIBED_MAPS = """
SELECT
    m.id, m.owner_id, m.name, m.description, m.is_public, m.public_read_only,
    m.edge_type, m.rankdir, m.auto_layout, m.node_sep, m.rank_sep, m.location_tracking_enabled,
    m.date_created, m.date_updated,
    NOT m.public_read_only AS edit_access
FROM map m
JOIN map_subscription ms ON m.id = ms.map_id
WHERE ms.user_id = $1 AND m.is_public = true
ORDER BY m.date_updated DESC;
"""

INSERT_SUBSCRIPTION = """
INSERT INTO map_subscription (map_id, user_id)
VALUES ($1, $2)
ON CONFLICT (map_id, user_id) DO NOTHING;
"""

DELETE_SUBSCRIPTION = """
DELETE FROM map_subscription
WHERE map_id = $1 AND user_id = $2;
"""

GET_SUBSCRIPTION_COUNT = """
SELECT COUNT(*)::int FROM map_subscription WHERE map_id = $1;
"""

CHECK_MAP_PUBLIC = """
SELECT is_public FROM map WHERE id = $1;
"""

# Signature queries

GET_MAP_SIGNATURES = """
SELECT
    s.id, s.node_id, s.code, s.group_type, s.subgroup, s.type,
    s.link_id,
    COALESCE(lw.code, sw.code) AS wormhole_code
FROM signature s
LEFT JOIN link l ON s.link_id = l.id
LEFT JOIN wormhole lw ON l.wormhole_id = lw.id
LEFT JOIN wormhole sw ON s.wormhole_id = sw.id
WHERE s.map_id = $1 AND s.date_deleted IS NULL
ORDER BY s.node_id, s.code;
"""

GET_NODE_SIGNATURES = """
SELECT
    s.id, s.node_id, s.code, s.group_type, s.subgroup, s.type,
    s.link_id,
    COALESCE(lw.code, sw.code) AS wormhole_code
FROM signature s
LEFT JOIN link l ON s.link_id = l.id
LEFT JOIN wormhole lw ON l.wormhole_id = lw.id
LEFT JOIN wormhole sw ON s.wormhole_id = sw.id
WHERE s.node_id = $1 AND s.map_id = $2 AND s.date_deleted IS NULL
ORDER BY s.code;
"""

GET_SIGNATURE_ENRICHED = """
SELECT
    s.id, s.node_id, s.code, s.group_type, s.subgroup, s.type,
    s.link_id,
    COALESCE(lw.code, sw.code) AS wormhole_code
FROM signature s
LEFT JOIN link l ON s.link_id = l.id
LEFT JOIN wormhole lw ON l.wormhole_id = lw.id
LEFT JOIN wormhole sw ON s.wormhole_id = sw.id
WHERE s.id = $1 AND s.date_deleted IS NULL;
"""

INSERT_SIGNATURE = """
INSERT INTO signature (node_id, map_id, code, group_type, subgroup, type, link_id, wormhole_id)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
RETURNING id;
"""

DELETE_SIGNATURE = """
UPDATE signature
SET date_deleted = NOW(), date_updated = NOW()
WHERE id = $1 AND map_id = $2 AND date_deleted IS NULL
RETURNING id;
"""

GET_SIGNATURE_MAP_ID = """
SELECT map_id FROM signature WHERE id = $1;
"""

SOFT_DELETE_NODE_SIGNATURES = """
UPDATE signature
SET date_deleted = NOW(), date_updated = NOW()
WHERE node_id = $1 AND map_id = $2 AND date_deleted IS NULL
RETURNING id;
"""

GET_NODE_SIGNATURE_IDS = """
SELECT id FROM signature
WHERE node_id = $1 AND date_deleted IS NULL;
"""

UPSERT_SIGNATURE = """
INSERT INTO signature (node_id, map_id, code, group_type, subgroup, type)
VALUES ($1, $2, $3, $4, $5, $6)
ON CONFLICT (node_id, code) WHERE date_deleted IS NULL
DO UPDATE SET
    group_type = EXCLUDED.group_type,
    subgroup = EXCLUDED.subgroup,
    type = EXCLUDED.type,
    date_updated = NOW()
RETURNING id, code, (xmax = 0) AS is_insert;
"""

# Batch fetch enriched signatures by IDs
GET_SIGNATURES_ENRICHED_BATCH = """
SELECT
    s.id, s.node_id, s.code, s.group_type, s.subgroup, s.type,
    s.link_id,
    w.code AS wormhole_code
FROM signature s
LEFT JOIN link l ON s.link_id = l.id
LEFT JOIN wormhole w ON l.wormhole_id = w.id
WHERE s.id = ANY($1) AND s.date_deleted IS NULL;
"""

GET_SIGNATURE_BY_NODE_CODE = """
SELECT id, date_created, date_updated FROM signature
WHERE node_id = $1 AND code = $2 AND date_deleted IS NULL;
"""

FIND_SIGNATURES_BY_NODE = """
SELECT id, code FROM signature
WHERE node_id = $1 AND date_deleted IS NULL;
"""

DELETE_SIGNATURES_NOT_IN_CODES = """
UPDATE signature
SET date_deleted = NOW(), date_updated = NOW()
WHERE node_id = $1 AND date_deleted IS NULL AND code != ALL($2)
RETURNING id;
"""

# Node connections query - get all links connected to a node with system names
GET_NODE_CONNECTIONS = """
SELECT
    l.id, l.source_node_id, l.target_node_id,
    w.code AS wormhole_code,
    sn_sys.name AS source_system_name,
    tn_sys.name AS target_system_name
FROM link l
LEFT JOIN wormhole w ON l.wormhole_id = w.id
JOIN node sn ON l.source_node_id = sn.id
JOIN node tn ON l.target_node_id = tn.id
JOIN system sn_sys ON sn.system_id = sn_sys.id
JOIN system tn_sys ON tn.system_id = tn_sys.id
WHERE (l.source_node_id = $1 OR l.target_node_id = $1)
  AND l.map_id = $2
  AND l.date_deleted IS NULL
ORDER BY l.id;
"""

# Get link source and target node IDs for flip logic
GET_LINK_NODES = """
SELECT source_node_id, target_node_id, wormhole_id
FROM link
WHERE id = $1 AND map_id = $2 AND date_deleted IS NULL;
"""

# Reverse link direction (swap source and target)
REVERSE_LINK = """
UPDATE link
SET source_node_id = target_node_id,
    target_node_id = source_node_id,
    date_updated = NOW()
WHERE id = $1 AND map_id = $2 AND date_deleted IS NULL;
"""

# Flip link direction and set wormhole type
FLIP_LINK_DIRECTION = """
UPDATE link
SET source_node_id = target_node_id,
    target_node_id = source_node_id,
    wormhole_id = $2,
    date_updated = NOW()
WHERE id = $1 AND map_id = $3 AND date_deleted IS NULL
RETURNING id;
"""

# Get signature with node_id for connection creation
GET_SIGNATURE_NODE = """
SELECT node_id, map_id FROM signature
WHERE id = $1 AND map_id = $2 AND date_deleted IS NULL;
"""

# Update signature link_id
UPDATE_SIGNATURE_LINK = """
UPDATE signature
SET link_id = $2, date_updated = NOW()
WHERE id = $1 AND map_id = $3 AND date_deleted IS NULL
RETURNING id;
"""

# Node lock queries
GET_NODE_LOCKED = """
SELECT locked FROM node WHERE id = $1 AND map_id = $2 AND date_deleted IS NULL;
"""

UPDATE_NODE_LOCKED = """
UPDATE node
SET locked = $2, date_updated = NOW()
WHERE id = $1 AND map_id = $3 AND date_deleted IS NULL
RETURNING id;
"""

# Note queries

GET_SYSTEM_NOTES = """
SELECT
    n.id, n.solar_system_id, n.map_id, n.title, n.content,
    n.created_by, cc.name AS created_by_name,
    n.updated_by, uc.name AS updated_by_name,
    n.date_expires, n.date_created, n.date_updated
FROM note n
JOIN character cc ON n.created_by = cc.id
LEFT JOIN character uc ON n.updated_by = uc.id
WHERE n.solar_system_id = $1 AND n.map_id = $2 AND n.date_deleted IS NULL
ORDER BY n.date_created DESC;
"""

GET_NOTE_ENRICHED = """
SELECT
    n.id, n.solar_system_id, n.map_id, n.title, n.content,
    n.created_by, cc.name AS created_by_name,
    n.updated_by, uc.name AS updated_by_name,
    n.date_expires, n.date_created, n.date_updated
FROM note n
JOIN character cc ON n.created_by = cc.id
LEFT JOIN character uc ON n.updated_by = uc.id
WHERE n.id = $1 AND n.date_deleted IS NULL;
"""

INSERT_NOTE = """
INSERT INTO note (solar_system_id, map_id, title, content, created_by, date_expires)
VALUES ($1, $2, $3, $4, $5, $6)
RETURNING id;
"""

UPDATE_NOTE = """
UPDATE note
SET title = $2,
    content = COALESCE($3, content),
    date_expires = $4,
    updated_by = $5,
    date_updated = NOW()
WHERE id = $1 AND map_id = $6 AND date_deleted IS NULL
RETURNING id;
"""

DELETE_NOTE = """
UPDATE note
SET date_deleted = NOW(), date_updated = NOW()
WHERE id = $1 AND map_id = $2 AND date_deleted IS NULL
RETURNING id;
"""

GET_NOTE_MAP_ID = """
SELECT map_id FROM note WHERE id = $1;
"""

# Character location queries

GET_USER_MAPS_WITH_LOCATION_TRACKING = """
SELECT DISTINCT m.id
FROM map m
LEFT JOIN map_character mc ON m.id = mc.map_id
    AND mc.character_id IN (SELECT id FROM character WHERE user_id = $1)
LEFT JOIN map_corporation mcorp ON m.id = mcorp.map_id AND mcorp.corporation_id = $2
LEFT JOIN map_alliance ma ON m.id = ma.map_id AND ma.alliance_id = $3
LEFT JOIN map_subscription ms ON m.id = ms.map_id AND ms.user_id = $1
WHERE m.location_tracking_enabled = true
    AND m.date_deleted IS NULL
    AND (
        m.owner_id = $1
        OR mc.map_id IS NOT NULL
        OR mcorp.map_id IS NOT NULL
        OR ma.map_id IS NOT NULL
        OR (ms.map_id IS NOT NULL AND m.is_public = true)
    );
"""

GET_NODES_FOR_SYSTEM_IN_MAPS = """
SELECT n.id AS node_id, n.map_id
FROM node n
WHERE n.system_id = $1
    AND n.map_id = ANY($2::uuid[])
    AND n.date_deleted IS NULL;
"""

GET_MAP_CHARACTERS_WITH_LOCATION_SCOPE = """
SELECT
    c.id AS character_id,
    c.name AS character_name,
    corp.name AS corporation_name,
    alliance.name AS alliance_name
FROM character c
JOIN refresh_token rt ON rt.character_id = c.id AND rt.has_location_scope = true
LEFT JOIN corporation corp ON corp.id = c.corporation_id
LEFT JOIN alliance ON alliance.id = c.alliance_id
WHERE c.user_id IN (
    SELECT DISTINCT u.id FROM "user" u
    LEFT JOIN character uc ON uc.user_id = u.id
    LEFT JOIN map_character mc ON mc.character_id = uc.id AND mc.map_id = $1
    LEFT JOIN map_corporation mcorp ON mcorp.map_id = $1 AND mcorp.corporation_id = uc.corporation_id
    LEFT JOIN map_alliance ma ON ma.map_id = $1 AND ma.alliance_id = uc.alliance_id
    LEFT JOIN map_subscription ms ON ms.map_id = $1 AND ms.user_id = u.id
    JOIN map m ON m.id = $1
    WHERE m.owner_id = u.id
        OR mc.map_id IS NOT NULL
        OR mcorp.map_id IS NOT NULL
        OR ma.map_id IS NOT NULL
        OR (ms.map_id IS NOT NULL AND m.is_public = true)
);
"""
