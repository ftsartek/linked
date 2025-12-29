"""SQL queries for universe search endpoints."""

# Search systems by name with trigram similarity
# Exact/prefix matches come first, then trigram similarity matches
from __future__ import annotations

SEARCH_SYSTEMS = """\
SELECT id, name, wh_class
FROM system
WHERE name ILIKE $1 OR name % $2
ORDER BY
    CASE WHEN name ILIKE $1 THEN 0 ELSE 1 END,
    similarity(name, $2) DESC
LIMIT 20;
"""

# Search wormholes by code with trigram similarity
# Supports optional filtering by destination and source
SEARCH_WORMHOLES = """\
SELECT id, code
FROM wormhole
WHERE (code ILIKE $1 OR code % $2)
  AND ($3::text IS NULL OR destination = $3)
  AND ($4::text IS NULL OR $4 = ANY(sources))
ORDER BY
    CASE WHEN code ILIKE $1 THEN 0 ELSE 1 END,
    similarity(code, $2) DESC
LIMIT 20;
"""
