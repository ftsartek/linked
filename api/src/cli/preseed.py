from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import asyncclick as click
import yaml

from database import init_db, provide_session

if TYPE_CHECKING:
    from sqlspec.adapters.asyncpg import AsyncpgDriver

PRESEED_DIR = Path(__file__).parent.parent.parent / "static" / "preseed"


def load_yaml(filename: str) -> dict | list:
    """Load a YAML file from the preseed directory."""
    with open(PRESEED_DIR / filename) as f:
        return yaml.safe_load(f)


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


async def import_regions(session: AsyncpgDriver, regions_data: list) -> None:
    """Import regions."""
    click.echo(f"Importing {len(regions_data)} regions...")
    rows = [(r["region_id"], r["name"], r.get("description")) for r in regions_data]
    await session.execute_many(
        """INSERT INTO region (id, name, description) VALUES ($1, $2, $3)
           ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description""",
        rows,
    )


def merge_wormhole_data(info_data: dict, spawns_data: dict) -> dict[str, dict]:
    """Merge wormhole_info and wormhole_spawns into a code-keyed dict.

    Since multiple typeIDs can map to the same code, we merge target lists
    and use the first encountered typeID for other values.
    """
    merged: dict[str, dict] = {}

    for type_id_str, info in info_data.items():
        type_id = int(type_id_str)
        code = info["code"]
        spawns = spawns_data.get(type_id_str, spawns_data.get(type_id, {}))

        if code not in merged:
            # First typeID for this code - initialize
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
            # Merge target lists from additional typeIDs
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
        """INSERT INTO wormhole (code, eve_type_id, sources, target_class, mass_total, mass_jump_max, mass_regen, lifetime, target_regions, target_constellations, target_systems)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
           ON CONFLICT (code) DO UPDATE SET
               eve_type_id = EXCLUDED.eve_type_id, sources = EXCLUDED.sources, target_class = EXCLUDED.target_class,
               mass_total = EXCLUDED.mass_total, mass_jump_max = EXCLUDED.mass_jump_max, mass_regen = EXCLUDED.mass_regen,
               lifetime = EXCLUDED.lifetime, target_regions = EXCLUDED.target_regions,
               target_constellations = EXCLUDED.target_constellations, target_systems = EXCLUDED.target_systems""",
        rows,
    )
    return {row["code"]: row["id"] for row in await session.select("SELECT id, code FROM wormhole")}


async def import_constellations(session: AsyncpgDriver, constellations_data: list) -> None:
    """Import constellations."""
    click.echo(f"Importing {len(constellations_data)} constellations...")
    rows = [(c["constellation_id"], c["region_id"], c["name"]) for c in constellations_data]
    await session.execute_many(
        """INSERT INTO constellation (id, region_id, name) VALUES ($1, $2, $3)
           ON CONFLICT (id) DO UPDATE SET region_id = EXCLUDED.region_id, name = EXCLUDED.name""",
        rows,
    )


async def import_systems(session: AsyncpgDriver, systems_data: list) -> None:
    """Import systems."""
    click.echo(f"Importing {len(systems_data)} systems...")
    rows = [
        (
            s["system_id"],
            s["constellation_id"],
            s["name"],
            s.get("security_status"),
            s.get("security_class"),
            s.get("star_id"),
            None,  # wh_class
            None,  # wh_effect_id
        )
        for s in systems_data
    ]
    await session.execute_many(
        """INSERT INTO system (id, constellation_id, name, security_status, security_class, star_id, wh_class, wh_effect_id)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
           ON CONFLICT (id) DO UPDATE SET
               constellation_id = EXCLUDED.constellation_id, name = EXCLUDED.name,
               security_status = EXCLUDED.security_status, security_class = EXCLUDED.security_class, star_id = EXCLUDED.star_id""",
        rows,
    )


async def update_wormhole_systems(
    session: AsyncpgDriver,
    wormhole_systems_data: dict,
    systems_data: list,
    effect_name_to_id: dict[str, int],
    wormhole_code_to_id: dict[str, int],
) -> list[tuple[int, int]]:
    """Update wormhole systems with WH-specific data and return statics to insert."""
    click.echo(f"Updating {len(wormhole_systems_data)} wormhole systems...")

    # Build set of known system IDs for validation
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

        wh_update_rows.append((wh_data.get("class"), effect_id, system_id))

        for static_code in wh_data.get("statics") or []:
            wormhole_id = wormhole_code_to_id.get(static_code)
            if wormhole_id:
                statics_to_insert.append((system_id, wormhole_id))

    await session.execute_many(
        "UPDATE system SET wh_class = $1, wh_effect_id = $2 WHERE id = $3",
        wh_update_rows,
    )
    return statics_to_insert


async def import_system_statics(session: AsyncpgDriver, statics_to_insert: list[tuple[int, int]]) -> None:
    """Import system statics (many-to-many relationship). Replaces all existing statics for WH systems."""
    # Delete existing statics for wormhole systems (full replace)
    await session.execute(
        "DELETE FROM system_static WHERE system_id IN (SELECT id FROM system WHERE wh_class IS NOT NULL)"
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

    # Delete systems not in import
    system_ids = [s["system_id"] for s in systems_data]
    await session.execute(
        "DELETE FROM system WHERE id != ALL($1::int[])",
        [system_ids],
    )

    # Delete constellations not in import
    constellation_ids = [c["constellation_id"] for c in constellations_data]
    await session.execute(
        "DELETE FROM constellation WHERE id != ALL($1::int[])",
        [constellation_ids],
    )

    # Delete regions not in import
    region_ids = [r["region_id"] for r in regions_data]
    await session.execute(
        "DELETE FROM region WHERE id != ALL($1::int[])",
        [region_ids],
    )

    # Delete wormholes not in import
    wormhole_codes = list(wormholes_data.keys())
    await session.execute(
        "DELETE FROM wormhole WHERE code != ALL($1::text[])",
        [wormhole_codes],
    )

    # Delete effects not in import
    effect_names = list(effects_data.keys())
    await session.execute(
        "DELETE FROM effect WHERE name != ALL($1::text[])",
        [effect_names],
    )


@click.command()
async def preseed() -> None:
    """Import static universe data into the database."""
    click.echo("Initializing database tables...")
    await init_db()

    click.echo("Loading YAML files...")
    effects_data = load_yaml("effects.yaml")
    regions_data = load_yaml("regions.yaml")
    wormhole_info_data = load_yaml("wormhole_info.yaml")
    wormhole_spawns_data = load_yaml("wormhole_spawns.yaml")
    wormholes_data = merge_wormhole_data(wormhole_info_data, wormhole_spawns_data)
    constellations_data = load_yaml("constellations.yaml")
    systems_data = load_yaml("systems.yaml")
    wormhole_systems_data = load_yaml("wormhole_systems.yaml")

    async with provide_session() as session:
        # Import in dependency order
        effect_name_to_id = await import_effects(session, effects_data)
        await import_regions(session, regions_data)
        wormhole_code_to_id = await import_wormholes(session, wormholes_data)
        await import_constellations(session, constellations_data)
        await import_systems(session, systems_data)

        # Update wormhole systems and get statics
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
