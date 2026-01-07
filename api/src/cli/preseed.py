from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import asyncclick as click
import yaml

from database import init_db, provide_session

if TYPE_CHECKING:
    from sqlspec.adapters.asyncpg import AsyncpgDriver

# Static directory (baked into container)
STATIC_DIR = Path(__file__).parent.parent.parent / "static"
CURATED_DIR = STATIC_DIR / "preseed" / "curated"

# Dynamic data directory (configurable via env var, defaults to static/preseed for dev compatibility)
_default_data_dir = STATIC_DIR / "preseed"
DATA_DIR = Path(os.environ.get("DATA_DIR", str(_default_data_dir)))
SDE_DIR = DATA_DIR / "sde"

# Unidentified placeholder systems with negative IDs
# Format: (id, system_class, name)
UNIDENTIFIED_SYSTEMS = [
    (-1, 0, "Unidentified"),
    (-2, 1, "Unidentified"),
    (-3, 2, "Unidentified"),
    (-4, 3, "Unidentified"),
    (-5, 4, "Unidentified"),
    (-6, 5, "Unidentified"),
    (-7, 6, "Unidentified"),
    (-8, 7, "Unidentified"),
    (-9, 8, "Unidentified"),
    (-10, 9, "Unidentified"),
    (-11, 13, "Unidentified"),
]


def load_yaml(filename: str, directory: Path = DATA_DIR) -> dict | list:
    """Load a YAML file from the specified directory."""
    with open(directory / filename) as f:
        return yaml.safe_load(f)


def load_yaml_dict(filename: str, directory: Path = DATA_DIR) -> dict:
    """Load a YAML file that contains a dict at root level."""
    result = load_yaml(filename, directory)
    if not isinstance(result, dict):
        raise TypeError(f"Expected dict in {filename}, got {type(result).__name__}")
    return result


def load_yaml_list(filename: str, directory: Path = DATA_DIR) -> list:
    """Load a YAML file that contains a list at root level."""
    result = load_yaml(filename, directory)
    if not isinstance(result, list):
        raise TypeError(f"Expected list in {filename}, got {type(result).__name__}")
    return result


def load_sde_data() -> tuple[dict, dict, dict]:
    """Load SDE map data files and return (regions, constellations, systems) dicts."""
    click.echo("Loading SDE data...")
    sde_regions = load_yaml_dict("mapRegions.yaml", SDE_DIR)
    sde_constellations = load_yaml_dict("mapConstellations.yaml", SDE_DIR)
    sde_systems = load_yaml_dict("mapSolarSystems.yaml", SDE_DIR)
    return sde_regions, sde_constellations, sde_systems


def build_fallback_lookups(
    sde_regions: dict,
    sde_constellations: dict,
) -> tuple[dict[int, int | None], dict[int, int | None], dict[int, int | None], dict[int, int | None]]:
    """Build lookup dicts for wormhole_class_id and faction_id fallbacks.

    Returns:
        (region_wh_class, region_faction, constellation_wh_class, constellation_faction)
    """
    region_wh_class: dict[int, int | None] = {}
    region_faction: dict[int, int | None] = {}
    constellation_wh_class: dict[int, int | None] = {}
    constellation_faction: dict[int, int | None] = {}

    for region_id, data in sde_regions.items():
        region_wh_class[region_id] = data.get("wormholeClassID")
        region_faction[region_id] = data.get("factionID")

    for const_id, data in sde_constellations.items():
        constellation_wh_class[const_id] = data.get("wormholeClassID")
        constellation_faction[const_id] = data.get("factionID")

    return region_wh_class, region_faction, constellation_wh_class, constellation_faction


def resolve_system_class(
    system_data: dict,
    constellation_id: int,
    sde_constellations: dict,
    region_wh_class: dict[int, int | None],
    constellation_wh_class: dict[int, int | None],
) -> int:
    """Resolve system_class with fallback: system -> constellation -> region -> 0."""
    # Try system level
    if (wh_class := system_data.get("wormholeClassID")) is not None:
        return wh_class

    # Try constellation level
    if (wh_class := constellation_wh_class.get(constellation_id)) is not None:
        return wh_class

    # Try region level
    const_data = sde_constellations.get(constellation_id, {})
    region_id = const_data.get("regionID")
    if region_id and (wh_class := region_wh_class.get(region_id)) is not None:
        return wh_class

    # Default to 0
    return 0


def resolve_faction_id(
    system_data: dict,
    constellation_id: int,
    sde_constellations: dict,
    region_faction: dict[int, int | None],
    constellation_faction: dict[int, int | None],
) -> int:
    """Resolve faction_id with fallback: system -> constellation -> region -> 0."""
    # Try system level
    if (faction_id := system_data.get("factionID")) is not None:
        return faction_id

    # Try constellation level
    if (faction_id := constellation_faction.get(constellation_id)) is not None:
        return faction_id

    # Try region level
    const_data = sde_constellations.get(constellation_id, {})
    region_id = const_data.get("regionID")
    if region_id and (faction_id := region_faction.get(region_id)) is not None:
        return faction_id

    # Default to 0
    return 0


async def import_effects(session: AsyncpgDriver, effects_data: dict) -> dict[str, int]:
    """Import effects and return name -> db_id mapping."""
    click.echo(f"Importing {len(effects_data)} effects...")
    rows = [(name, data.get("buffs"), data.get("debuffs")) for name, data in effects_data.items()]
    await session.execute_many(
        """INSERT INTO effect (name, buffs, debuffs) VALUES ($1, $2, $3)
           ON CONFLICT (name) DO UPDATE SET buffs = EXCLUDED.buffs, debuffs = EXCLUDED.debuffs""",
        rows,
    )
    return {row["name"]: row["id"] for row in await session.select("SELECT id, name FROM effect")}


async def import_regions(session: AsyncpgDriver, regions_data: list, sde_regions: dict) -> None:
    """Import regions with SDE wormhole_class_id and faction_id."""
    click.echo(f"Importing {len(regions_data)} regions...")
    rows = []
    for r in regions_data:
        region_id = r["region_id"]
        sde_data = sde_regions.get(region_id, {})
        rows.append(
            (
                region_id,
                r["name"],
                r.get("description"),
                sde_data.get("wormholeClassID"),
                sde_data.get("factionID"),
            )
        )
    await session.execute_many(
        """INSERT INTO region (id, name, description, wormhole_class_id, faction_id) VALUES ($1, $2, $3, $4, $5)
           ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description,
               wormhole_class_id = EXCLUDED.wormhole_class_id, faction_id = EXCLUDED.faction_id""",
        rows,
    )


def merge_wormhole_data(info_data: dict, spawns_data: dict) -> dict[str, dict]:
    """Merge wormhole_info and wormhole_spawns into a code-keyed dict."""
    merged: dict[str, dict] = {}

    for type_id_str, info in info_data.items():
        type_id = int(type_id_str)
        code = info["code"]
        spawns = spawns_data.get(type_id_str, spawns_data.get(type_id, {}))

        if code not in merged:
            merged[code] = {
                "typeID": type_id,
                "sources": spawns.get("sources"),
                "target_class": info.get("target_class"),
                "mass_total": info.get("mass_total"),
                "mass_jump_max": info.get("mass_jump_max"),
                "mass_regen": info.get("mass_regen"),
                "lifetime": info.get("lifetime"),
                "target_regions": info.get("target_regions", []),
                "target_constellations": info.get("target_constellations", []),
                "target_systems": info.get("target_systems", []),
            }
        else:
            existing = merged[code]
            for key in ["target_regions", "target_constellations", "target_systems"]:
                new_values = info.get(key, [])
                existing[key] = list(set(existing.get(key, []) + new_values))

    return merged


async def import_wormholes(session: AsyncpgDriver, wormholes_data: dict) -> dict[str, int]:
    """Import wormhole types and return code -> db_id mapping."""
    click.echo(f"Importing {len(wormholes_data)} wormhole types...")
    rows = [
        (
            code,
            data.get("typeID"),
            data.get("sources"),
            data.get("target_class"),
            data.get("mass_total"),
            data.get("mass_jump_max"),
            data.get("mass_regen"),
            data.get("lifetime"),
            data.get("target_regions"),
            data.get("target_constellations"),
            data.get("target_systems"),
        )
        for code, data in wormholes_data.items()
    ]
    await session.execute_many(
        """INSERT INTO wormhole
            (code, eve_type_id, sources, target_class, mass_total, mass_jump_max, mass_regen,
             lifetime, target_regions, target_constellations, target_systems)
        VALUES
            ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        ON CONFLICT (code) DO UPDATE SET
            eve_type_id = EXCLUDED.eve_type_id, sources = EXCLUDED.sources, target_class = EXCLUDED.target_class,
            mass_total = EXCLUDED.mass_total, mass_jump_max = EXCLUDED.mass_jump_max,
            mass_regen = EXCLUDED.mass_regen, lifetime = EXCLUDED.lifetime,
            target_regions = EXCLUDED.target_regions, target_constellations = EXCLUDED.target_constellations,
            target_systems = EXCLUDED.target_systems""",
        rows,
    )
    return {row["code"]: row["id"] for row in await session.select("SELECT id, code FROM wormhole")}


async def import_constellations(session: AsyncpgDriver, constellations_data: list, sde_constellations: dict) -> None:
    """Import constellations with SDE wormhole_class_id and faction_id."""
    click.echo(f"Importing {len(constellations_data)} constellations...")
    rows = []
    for c in constellations_data:
        const_id = c["constellation_id"]
        sde_data = sde_constellations.get(const_id, {})
        rows.append(
            (
                const_id,
                c["region_id"],
                c["name"],
                sde_data.get("wormholeClassID"),
                sde_data.get("factionID"),
            )
        )
    await session.execute_many(
        """INSERT INTO constellation (id, region_id, name, wormhole_class_id, faction_id) VALUES ($1, $2, $3, $4, $5)
           ON CONFLICT (id) DO UPDATE SET region_id = EXCLUDED.region_id, name = EXCLUDED.name,
               wormhole_class_id = EXCLUDED.wormhole_class_id, faction_id = EXCLUDED.faction_id""",
        rows,
    )


async def import_systems(
    session: AsyncpgDriver,
    systems_data: list,
    sde_systems: dict,
    sde_constellations: dict,
    region_wh_class: dict[int, int | None],
    region_faction: dict[int, int | None],
    constellation_wh_class: dict[int, int | None],
    constellation_faction: dict[int, int | None],
) -> None:
    """Import systems with resolved system_class and faction_id from SDE."""
    click.echo(f"Importing {len(systems_data)} systems...")
    rows = []
    for s in systems_data:
        system_id = s["system_id"]
        constellation_id = s["constellation_id"]
        sde_data = sde_systems.get(system_id, {})

        # Get position2D for pos_x/pos_y
        pos_2d = sde_data.get("position2D", {})

        # Resolve system_class and faction_id with fallback
        system_class = resolve_system_class(
            sde_data, constellation_id, sde_constellations, region_wh_class, constellation_wh_class
        )
        faction_id = resolve_faction_id(
            sde_data, constellation_id, sde_constellations, region_faction, constellation_faction
        )

        rows.append(
            (
                system_id,
                constellation_id,
                s["name"],
                s.get("security_status"),
                s.get("security_class"),
                system_class,
                faction_id,
                s.get("star_id"),
                sde_data.get("radius"),
                pos_2d.get("x"),
                pos_2d.get("y"),
                sde_data.get("stargateIDs"),
                None,  # wh_effect_id - set later
            )
        )
    await session.execute_many(
        """INSERT INTO system
            (id, constellation_id, name, security_status, security_class, system_class,
             faction_id, star_id, radius, pos_x, pos_y, stargate_ids, wh_effect_id)
        VALUES
            ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
        ON CONFLICT (id) DO UPDATE SET
            constellation_id = EXCLUDED.constellation_id, name = EXCLUDED.name,
            security_status = EXCLUDED.security_status, security_class = EXCLUDED.security_class,
            system_class = EXCLUDED.system_class, faction_id = EXCLUDED.faction_id,
            star_id = EXCLUDED.star_id, radius = EXCLUDED.radius, pos_x = EXCLUDED.pos_x, pos_y = EXCLUDED.pos_y,
            stargate_ids = EXCLUDED.stargate_ids""",
        rows,
    )


async def update_wormhole_systems(
    session: AsyncpgDriver,
    wormhole_systems_data: dict,
    systems_data: list,
    effect_name_to_id: dict[str, int],
    wormhole_code_to_id: dict[str, int],
) -> list[tuple[int, int]]:
    """Update wormhole systems with effect data and return statics to insert."""
    click.echo(f"Updating {len(wormhole_systems_data)} wormhole systems...")

    known_system_ids = {s["system_id"] for s in systems_data}

    wh_update_rows = []
    statics_to_insert: list[tuple[int, int]] = []

    for system_id_str, wh_data in wormhole_systems_data.items():
        system_id = int(system_id_str)

        if system_id not in known_system_ids:
            click.echo(f"  Warning: System {system_id} not found in systems.yaml, skipping")
            continue

        effect_name = wh_data.get("effect")
        effect_id = effect_name_to_id.get(effect_name) if effect_name else None

        wh_update_rows.append((effect_id, system_id))

        for static_code in wh_data.get("statics") or []:
            wormhole_id = wormhole_code_to_id.get(static_code)
            if wormhole_id:
                statics_to_insert.append((system_id, wormhole_id))

    await session.execute_many(
        "UPDATE system SET wh_effect_id = $1 WHERE id = $2",
        wh_update_rows,
    )
    return statics_to_insert


async def import_unidentified_systems(session: AsyncpgDriver) -> None:
    """Import unidentified placeholder systems with negative IDs."""
    click.echo(f"Importing {len(UNIDENTIFIED_SYSTEMS)} unidentified systems...")
    rows = [
        (
            system_id,  # id
            None,  # constellation_id
            name,  # name
            None,  # security_status
            None,  # security_class
            system_class,  # system_class
            None,  # faction_id
            None,  # star_id
            None,  # radius
            None,  # pos_x
            None,  # pos_y
            None,  # stargate_ids
            None,  # wh_effect_id
        )
        for system_id, system_class, name in UNIDENTIFIED_SYSTEMS
    ]
    await session.execute_many(
        """INSERT INTO system
            (id, constellation_id, name, security_status, security_class, system_class,
             faction_id, star_id, radius, pos_x, pos_y, stargate_ids, wh_effect_id)
        VALUES
            ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name, system_class = EXCLUDED.system_class""",
        rows,
    )


async def import_system_statics(session: AsyncpgDriver, statics_to_insert: list[tuple[int, int]]) -> None:
    """Import system statics (many-to-many relationship)."""
    await session.execute(
        "DELETE FROM system_static WHERE system_id IN \
        (SELECT id FROM system WHERE system_class IS NOT NULL AND system_class <= 18)"
    )

    click.echo(f"Inserting {len(statics_to_insert)} system statics...")
    if statics_to_insert:
        await session.execute_many(
            "INSERT INTO system_static (system_id, wormhole_id) VALUES ($1, $2)",
            statics_to_insert,
        )


async def cleanup_orphaned_records(
    session: AsyncpgDriver,
    effects_data: dict,
    regions_data: list,
    wormholes_data: dict,
    constellations_data: list,
    systems_data: list,
) -> None:
    """Delete records not in the current import (reverse FK order)."""
    click.echo("Cleaning up orphaned records...")

    system_ids = [s["system_id"] for s in systems_data]
    # Exclude negative IDs (unidentified systems) from cleanup
    await session.execute("DELETE FROM system WHERE id != ALL($1::int[]) AND id > 0", [system_ids])

    constellation_ids = [c["constellation_id"] for c in constellations_data]
    await session.execute("DELETE FROM constellation WHERE id != ALL($1::int[])", [constellation_ids])

    region_ids = [r["region_id"] for r in regions_data]
    await session.execute("DELETE FROM region WHERE id != ALL($1::int[])", [region_ids])

    wormhole_codes = list(wormholes_data.keys())
    await session.execute("DELETE FROM wormhole WHERE code != ALL($1::text[])", [wormhole_codes])

    effect_names = list(effects_data.keys())
    await session.execute("DELETE FROM effect WHERE name != ALL($1::text[])", [effect_names])


@click.command()
async def preseed() -> None:
    """Import static universe data into the database."""
    click.echo("Initializing database tables...")
    await init_db()

    click.echo("Loading YAML files...")
    # Curated data (manually maintained)
    effects_data = load_yaml_dict("effects.yaml", CURATED_DIR)
    wormhole_spawns_data = load_yaml_dict("wormhole_spawns.yaml", CURATED_DIR)
    wormhole_systems_data = load_yaml_dict("wormhole_systems.yaml", CURATED_DIR)
    # Generated data (from collect command)
    regions_data = load_yaml_list("regions.yaml")
    wormhole_info_data = load_yaml_dict("wormhole_info.yaml")
    wormholes_data = merge_wormhole_data(wormhole_info_data, wormhole_spawns_data)
    constellations_data = load_yaml_list("constellations.yaml")
    systems_data = load_yaml_list("systems.yaml")

    # Load SDE data for wormholeClassID and factionID
    sde_regions, sde_constellations, sde_systems = load_sde_data()

    # Build fallback lookup tables
    region_wh_class, region_faction, constellation_wh_class, constellation_faction = build_fallback_lookups(
        sde_regions, sde_constellations
    )

    async with provide_session() as session:
        # Import in dependency order
        effect_name_to_id = await import_effects(session, effects_data)
        await import_regions(session, regions_data, sde_regions)
        wormhole_code_to_id = await import_wormholes(session, wormholes_data)
        await import_constellations(session, constellations_data, sde_constellations)
        await import_systems(
            session,
            systems_data,
            sde_systems,
            sde_constellations,
            region_wh_class,
            region_faction,
            constellation_wh_class,
            constellation_faction,
        )
        await import_unidentified_systems(session)

        # Update wormhole systems with effect data and get statics
        statics_to_insert = await update_wormhole_systems(
            session,
            wormhole_systems_data,
            systems_data,
            effect_name_to_id,
            wormhole_code_to_id,
        )
        await import_system_statics(session, statics_to_insert)

        # Clean up orphaned records
        await cleanup_orphaned_records(
            session,
            effects_data,
            regions_data,
            wormholes_data,
            constellations_data,
            systems_data,
        )

    click.echo("Preseed complete!")
