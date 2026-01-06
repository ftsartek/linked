"""SQL queries for universe search endpoints."""

from __future__ import annotations

SEARCH_SYSTEMS = """\
SELECT id, name, system_class
FROM system
WHERE (name ILIKE $1 OR name % $2)
  AND id > 0
ORDER BY
    CASE WHEN name ILIKE $1 THEN 0 ELSE 1 END,
    similarity(name, $2) DESC
LIMIT 20;
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
ORDER BY rank_tier ASC, sim_score DESC
LIMIT 20;
"""

# List all unidentified placeholder systems (negative IDs)
LIST_UNIDENTIFIED_SYSTEMS = """\
SELECT id, name, system_class
FROM system
WHERE id < 0
ORDER BY system_class;
"""

# Search wormholes by code with trigram similarity
# Supports optional filtering by target_class and source (both integers)
SEARCH_WORMHOLES = """\
SELECT id, code
FROM wormhole
WHERE (code ILIKE $1 OR code % $2)
  AND ($3::int IS NULL OR target_class = $3)
  AND ($4::int IS NULL OR $4 = ANY(sources))
ORDER BY
    CASE WHEN code ILIKE $1 THEN 0 ELSE 1 END,
    similarity(code, $2) DESC
LIMIT 20;
"""
