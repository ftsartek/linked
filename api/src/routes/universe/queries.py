"""SQL queries for universe search endpoints."""

# Search systems by name with trigram similarity
# Exact/prefix matches come first, then trigram similarity matches
from __future__ import annotations

SEARCH_SYSTEMS = """\
SELECT id, name, system_class
FROM system
WHERE name ILIKE $1 OR name % $2
ORDER BY
    CASE WHEN name ILIKE $1 THEN 0 ELSE 1 END,
    similarity(name, $2) DESC
LIMIT 20;
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
