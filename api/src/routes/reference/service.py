from __future__ import annotations

from typing import TypedDict

from sqlspec import AsyncDriverAdapterBase, sql
from sqlspec.builder import Select

from routes.reference.dependencies import (
    WormholeConstellation,
    WormholeRegion,
    WormholeSystemItem,
    WormholeSystemsGrouped,
    WormholeSystemStatic,
    WormholeTypeDetail,
    WormholeTypeSummary,
)
from utils.class_mapping import SYSTEM_CLASS_MAPPING


class _ConstellationIndex(TypedDict):
    name: str
    systems: list[WormholeSystemItem]


class _RegionIndex(TypedDict):
    name: str
    constellations: dict[int, _ConstellationIndex]


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

GET_SYSTEM_STATICS_QUERY = """
SELECT ss.system_id, w.id, w.code, w.target_class
FROM system_static ss
JOIN wormhole w ON ss.wormhole_id = w.id
WHERE ss.system_id = ANY($1)
ORDER BY w.code
"""

# Wormhole system classes (C1-C6, Thera, C13, Drifter wormholes)
WORMHOLE_SYSTEM_CLASSES = (1, 2, 3, 4, 5, 6, 12, 13, 14, 15, 16, 17, 18)

# Shattered system classes (C13 and Drifter wormholes)
SHATTERED_SYSTEM_CLASSES = (13, 14, 15, 16, 17, 18)


def _build_wormhole_systems_query(
    system_classes: list[int] | None,
    effect_id: int | None,
    region_id: int | None,
    constellation_id: int | None,
    shattered: bool | None,
    static_id: int | None,
) -> tuple[Select, dict[str, int | bool | list[int]]]:
    """Build dynamic wormhole systems query with optional filters.

    Args:
        system_classes: Filter by wormhole class(es)
        effect_id: Filter by wormhole effect
        region_id: Filter by region
        constellation_id: Filter by constellation
        shattered: Filter by shattered status
        static_id: Filter by static wormhole type

    Returns:
        Tuple of (query builder, parameters dict)
    """
    q = (
        sql.select(
            "s.id",
            "s.name",
            "s.system_class",
            f"(s.system_class IN {SHATTERED_SYSTEM_CLASSES} OR s.name LIKE 'J0%') AS shattered",
            "s.wh_effect_id AS effect_id",
            "e.name AS effect_name",
            "c.id AS constellation_id",
            "c.name AS constellation_name",
            "r.id AS region_id",
            "r.name AS region_name",
        )
        .from_("system s")
        .join("constellation c", "s.constellation_id = c.id")
        .join("region r", "c.region_id = r.id")
        .left_join("effect e", "s.wh_effect_id = e.id")
        .where(f"s.system_class IN {WORMHOLE_SYSTEM_CLASSES}")
    )

    params: dict[str, int | bool | list[int]] = {}

    if system_classes is not None and len(system_classes) > 0:
        q = q.where("s.system_class = ANY(:system_classes)")
        params["system_classes"] = system_classes

    if effect_id is not None:
        q = q.where("s.wh_effect_id = :effect_id")
        params["effect_id"] = effect_id

    if region_id is not None:
        q = q.where("r.id = :region_id")
        params["region_id"] = region_id

    if constellation_id is not None:
        q = q.where("c.id = :constellation_id")
        params["constellation_id"] = constellation_id

    if shattered is not None:
        if shattered:
            q = q.where(f"(s.system_class IN {SHATTERED_SYSTEM_CLASSES} OR s.name LIKE 'J0%')")
        else:
            q = q.where(f"s.system_class NOT IN {SHATTERED_SYSTEM_CLASSES} AND s.name NOT LIKE 'J0%'")

    if static_id is not None:
        q = q.where(
            "EXISTS ("
            "SELECT 1 FROM system_static ss "
            "JOIN wormhole w ON ss.wormhole_id = w.id "
            "WHERE ss.system_id = s.id AND w.target_class = :static_id"
            ")"
        )
        params["static_id"] = static_id

    return q.order_by("s.name"), params


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

    async def list_wormhole_systems(
        self,
        system_classes: list[int] | None = None,
        effect_id: int | None = None,
        region_id: int | None = None,
        constellation_id: int | None = None,
        shattered: bool | None = None,
        static_id: int | None = None,
    ) -> WormholeSystemsGrouped:
        """List wormhole systems with optional filters, grouped by region and constellation.

        Args:
            system_classes: Filter by wormhole class(es) (1-6, 12, 13, 14-18)
            effect_id: Filter by wormhole effect
            region_id: Filter by region
            constellation_id: Filter by constellation
            shattered: Filter by shattered status
            static_id: Filter by static wormhole type

        Returns:
            Grouped wormhole systems (region -> constellation -> systems)
        """
        # Build and execute the main query
        query, params = _build_wormhole_systems_query(
            system_classes, effect_id, region_id, constellation_id, shattered, static_id
        )
        if params:
            rows = await self.db_session.select(query, params)
        else:
            rows = await self.db_session.select(query)

        if not rows:
            return WormholeSystemsGrouped(regions=[], total_systems=0)

        # Collect system IDs and fetch statics
        system_ids = [row["id"] for row in rows]
        static_rows = await self.db_session.select(GET_SYSTEM_STATICS_QUERY, [system_ids])

        # Build statics lookup by system_id
        statics_by_system: dict[int, list[WormholeSystemStatic]] = {}
        for static_row in static_rows:
            system_id = static_row["system_id"]
            if system_id not in statics_by_system:
                statics_by_system[system_id] = []
            statics_by_system[system_id].append(
                WormholeSystemStatic(
                    id=static_row["id"],
                    code=static_row["code"],
                    target_class=static_row["target_class"],
                    target_name=_get_class_name(static_row["target_class"]),
                )
            )

        # Group by region -> constellation -> systems
        region_index: dict[int, _RegionIndex] = {}
        for row in rows:
            region_id_val: int = row["region_id"]
            constellation_id_val: int = row["constellation_id"]

            if region_id_val not in region_index:
                region_index[region_id_val] = {
                    "name": row["region_name"],
                    "constellations": {},
                }

            constellations = region_index[region_id_val]["constellations"]
            if constellation_id_val not in constellations:
                constellations[constellation_id_val] = {
                    "name": row["constellation_name"],
                    "systems": [],
                }

            constellations[constellation_id_val]["systems"].append(
                WormholeSystemItem(
                    id=row["id"],
                    name=row["name"],
                    system_class=row["system_class"],
                    class_name=_get_class_name(row["system_class"]),
                    effect_id=row["effect_id"],
                    effect_name=row["effect_name"],
                    shattered=row["shattered"],
                    statics=statics_by_system.get(row["id"], []),
                )
            )

        # Convert to sorted list structure
        regions: list[WormholeRegion] = []
        for region_id_val in sorted(region_index.keys(), key=lambda r: region_index[r]["name"]):
            region_data = region_index[region_id_val]
            constellation_list: list[WormholeConstellation] = []

            for const_id in sorted(
                region_data["constellations"].keys(),
                key=lambda c: region_data["constellations"][c]["name"],
            ):
                const_data = region_data["constellations"][const_id]
                # Sort systems by name
                const_data["systems"].sort(key=lambda s: s.name)
                constellation_list.append(
                    WormholeConstellation(
                        id=const_id,
                        name=const_data["name"],
                        systems=const_data["systems"],
                    )
                )

            regions.append(
                WormholeRegion(
                    id=region_id_val,
                    name=region_data["name"],
                    constellations=constellation_list,
                )
            )

        return WormholeSystemsGrouped(regions=regions, total_systems=len(rows))


async def provide_reference_service(db_session: AsyncDriverAdapterBase) -> ReferenceService:
    """Provide ReferenceService with injected database session."""
    return ReferenceService(db_session)
