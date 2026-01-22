from __future__ import annotations

from sqlspec import AsyncDriverAdapterBase

from routes.reference.dependencies import WormholeTypeDetail, WormholeTypeSummary
from utils.class_mapping import SYSTEM_CLASS_MAPPING

LIST_WORMHOLES_QUERY = """
SELECT id, code, target_class, sources
FROM wormhole
ORDER BY
    CASE WHEN code = 'K162' THEN 1 ELSE 0 END,
    code
"""

GET_WORMHOLE_QUERY = """
SELECT id, code, target_class, sources, lifetime, mass_total, mass_jump_max, mass_regen
FROM wormhole
WHERE id = $1
"""


def _get_class_name(class_id: int | None) -> str:
    """Map a class ID to its display name."""
    if class_id is None:
        return "?"
    return SYSTEM_CLASS_MAPPING.get(class_id, "?")


def _get_class_names(class_ids: list[int] | None) -> list[str]:
    """Map a list of class IDs to their display names."""
    if class_ids is None:
        return []
    return [_get_class_name(class_id) for class_id in class_ids]


class ReferenceService:
    """Service for reference data lookups."""

    def __init__(self, db_session: AsyncDriverAdapterBase) -> None:
        self.db_session = db_session

    async def list_wormholes(self) -> list[WormholeTypeSummary]:
        """List all wormhole types with summary data."""
        return await self.db_session.select(
            LIST_WORMHOLES_QUERY,
            schema_type=WormholeTypeSummary,
        )

    async def get_wormhole(self, wormhole_id: int) -> WormholeTypeDetail | None:
        """Get detailed information for a specific wormhole type."""
        row = await self.db_session.select_one_or_none(GET_WORMHOLE_QUERY, wormhole_id)
        if row is None:
            return None

        return WormholeTypeDetail(
            id=row["id"],
            code=row["code"],
            target_class=row["target_class"],
            target_name=_get_class_name(row["target_class"]),
            sources=row["sources"],
            source_names=_get_class_names(row["sources"]),
            lifetime=row["lifetime"],
            mass_total=row["mass_total"],
            mass_jump_max=row["mass_jump_max"],
            mass_regen=row["mass_regen"],
        )


async def provide_reference_service(db_session: AsyncDriverAdapterBase) -> ReferenceService:
    """Provide ReferenceService with injected database session."""
    return ReferenceService(db_session)
