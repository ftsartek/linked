"""SQL queries for universe search endpoints."""

from __future__ import annotations

SEARCH_SYSTEMS = """\
SELECT id, name, system_class
FROM system
WHERE (name ILIKE $1 OR name % $2)
  AND id > 0
ORDER BY
    CASE WHEN name ILIKE $1 THEN 0 ELSE 1 END,
    similarity(name, $2) DESC;
"""

# Search local entities (characters, corporations, alliances) by name
# Results are sorted by: exact match > prefix match > trigram similarity
# Corporations and alliances also search by ticker
SEARCH_LOCAL_ENTITIES = """\
WITH ranked_entities AS (
    -- Characters
    SELECT
        id,
        name,
        'character' AS entity_type,
        NULL::text AS ticker,
        CASE
            WHEN LOWER(name) = LOWER($1) THEN 0
            WHEN name ILIKE $2 THEN 1
            ELSE 2
        END AS rank_tier,
        similarity(name, $1) AS sim_score
    FROM character
    WHERE name ILIKE $2 OR name % $1

    UNION ALL

    -- Corporations (search name and ticker)
    SELECT
        id,
        name,
        'corporation' AS entity_type,
        ticker,
        CASE
            WHEN LOWER(name) = LOWER($1) OR LOWER(ticker) = LOWER($1) THEN 0
            WHEN name ILIKE $2 OR ticker ILIKE $2 THEN 1
            ELSE 2
        END AS rank_tier,
        GREATEST(similarity(name, $1), similarity(ticker, $1)) AS sim_score
    FROM corporation
    WHERE name ILIKE $2 OR name % $1 OR ticker ILIKE $2 OR ticker % $1

    UNION ALL

    -- Alliances (search name and ticker)
    SELECT
        id,
        name,
        'alliance' AS entity_type,
        ticker,
        CASE
            WHEN LOWER(name) = LOWER($1) OR LOWER(ticker) = LOWER($1) THEN 0
            WHEN name ILIKE $2 OR ticker ILIKE $2 THEN 1
            ELSE 2
        END AS rank_tier,
        GREATEST(similarity(name, $1), similarity(ticker, $1)) AS sim_score
    FROM alliance
    WHERE name ILIKE $2 OR name % $1 OR ticker ILIKE $2 OR ticker % $1
)
SELECT id, name, entity_type, ticker
FROM ranked_entities
ORDER BY rank_tier ASC, sim_score DESC;
"""

# List all unidentified placeholder systems (negative IDs)
LIST_UNIDENTIFIED_SYSTEMS = """\
SELECT id, name, system_class
FROM system
WHERE id < 0
ORDER BY system_class;
"""

# Get system details including planet/moon/station counts and neighbours
GET_SYSTEM_DETAILS = """\
SELECT
    s.id,
    s.name,
    s.radius,
    (SELECT COUNT(*) FROM planet WHERE system_id = s.id) AS planet_count,
    (SELECT COUNT(*) FROM moon WHERE system_id = s.id) AS moon_count,
    (SELECT COUNT(*) FROM npc_station WHERE system_id = s.id) AS station_count,
    COALESCE(
        (SELECT json_agg(json_build_object(
            'id', dest.id,
            'name', dest.name,
            'security_status', dest.security_status,
            'system_class', dest.system_class
         ) ORDER BY dest.name)
         FROM stargate sg
         JOIN system dest ON sg.destination_system_id = dest.id
         WHERE sg.system_id = s.id),
        '[]'::json
    ) AS neighbours
FROM system s
WHERE s.id = $1;
"""
