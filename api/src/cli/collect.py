from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import asyncclick as click
import msgspec
import yaml

from esi_client import ESIClient
from esi_client.models import DogmaAttribute

STATIC_DIR = Path(__file__).parent.parent.parent / "static"

# Conservative rate limit: max 20 concurrent requests
MAX_CONCURRENT = 20


async def fetch_with_rate_limit[T](
    ids: list[int],
    fetch_fn: Callable[[int], Awaitable[T]],
    label: str,
) -> list[T]:
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    results: list[T] = []
    errors: list[tuple[int, Exception]] = []

    async def fetch_one(item_id: int) -> None:
        async with semaphore:
            try:
                result = await fetch_fn(item_id)
                results.append(result)
            except Exception as e:
                errors.append((item_id, e))

    total = len(ids)
    click.echo(f"Fetching {total} {label}...")

    tasks = [fetch_one(item_id) for item_id in ids]

    # Process with progress updates
    for i, coro in enumerate(asyncio.as_completed(tasks)):
        await coro
        if i % 100 == 0 or i == total - 1:
            click.echo(f"  Progress: {i + 1}/{total}")

    if errors:
        click.echo(f"  Warning: {len(errors)} errors occurred", err=True)
        for item_id, err in errors[:5]:
            click.echo(f"    ID {item_id}: {err}", err=True)
        if len(errors) > 5:
            click.echo(f"    ... and {len(errors) - 5} more", err=True)

    return results


def struct_to_dict(obj: object) -> dict:
    return msgspec.to_builtins(obj)


@click.group()
def collect() -> None:
    """Collect static data from ESI."""
    pass


@collect.command()
@click.option("--user-agent", envvar="LINKED_ESI_USER_AGENT", required=True)
async def regions(user_agent: str) -> None:
    """Collect all region data."""
    async with ESIClient(user_agent) as client:
        region_ids = await client.get_regions()
        region_list = await fetch_with_rate_limit(region_ids, client.get_region, "regions")

    # Sort by region_id for consistent output
    region_list.sort(key=lambda r: r.region_id)
    data = [struct_to_dict(r) for r in region_list]

    output_path = STATIC_DIR / "regions.yaml"
    with output_path.open("w") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)

    click.echo(f"Wrote {len(data)} regions to {output_path}")


@collect.command()
@click.option("--user-agent", envvar="LINKED_ESI_USER_AGENT", required=True)
async def constellations(user_agent: str) -> None:
    """Collect all constellation data."""
    async with ESIClient(user_agent) as client:
        constellation_ids = await client.get_constellations()
        constellation_list = await fetch_with_rate_limit(constellation_ids, client.get_constellation, "constellations")

    constellation_list.sort(key=lambda c: c.constellation_id)
    data = [struct_to_dict(c) for c in constellation_list]

    output_path = STATIC_DIR / "constellations.yaml"
    with output_path.open("w") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)

    click.echo(f"Wrote {len(data)} constellations to {output_path}")


@collect.command()
@click.option("--user-agent", envvar="LINKED_ESI_USER_AGENT", required=True)
async def systems(user_agent: str) -> None:
    """Collect all system data."""
    async with ESIClient(user_agent) as client:
        system_ids = await client.get_systems()
        system_list = await fetch_with_rate_limit(system_ids, client.get_system, "systems")

    system_list.sort(key=lambda s: s.system_id)
    data = [struct_to_dict(s) for s in system_list]

    output_path = STATIC_DIR / "systems.yaml"
    with output_path.open("w") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)

    click.echo(f"Wrote {len(data)} systems to {output_path}")


PRESEED_DIR = STATIC_DIR / "preseed"

# Wormhole group ID in ESI
WORMHOLE_GROUP_ID = 988

# Type IDs to skip (invalid/test wormholes)
SKIP_TYPE_IDS = {32894, 32895}

# Source string to class ID mapping
SOURCE_TO_CLASS_ID: dict[str, int] = {
    "c1": 1,
    "c2": 2,
    "c3": 3,
    "c4": 4,
    "c5": 5,
    "c6": 6,
    "hs": 7,
    "ls": 8,
    "ns": 9,
    "thera": 12,
    "c13": 13,
    "sentinel": 14,
    "barbican": 15,
    "vidette": 16,
    "redoubt": 17,
    "conflux": 18,
    "pv": 25,
}

# Dogma attribute IDs
ATTR_TARGET_CLASS = 1381
ATTR_LIFETIME = 1382
ATTR_MASS_TOTAL = 1383
ATTR_MASS_REGEN = 1384
ATTR_MASS_JUMP_MAX = 1385
ATTR_TARGET_REGIONS = range(1386, 1395)  # 1386-1394
ATTR_TARGET_CONSTELLATIONS = range(1395, 1404)  # 1395-1403
ATTR_TARGET_SYSTEMS = range(1404, 1413)  # 1404-1412


def parse_wormhole_dogma(dogma_attributes: list[DogmaAttribute] | None) -> dict[str, Any]:
    """Parse dogma attributes into wormhole info fields."""
    result: dict = {
        "lifetime": None,
        "target_class": None,
        "mass_total": None,
        "mass_jump_max": None,
        "mass_regen": None,
        "target_regions": [],
        "target_constellations": [],
        "target_systems": [],
    }

    if not dogma_attributes:
        return result

    for attr in dogma_attributes:
        attr_id = attr.attribute_id
        value = attr.value

        if attr_id == ATTR_TARGET_CLASS:
            result["target_class"] = int(value)
        elif attr_id == ATTR_LIFETIME:
            # Convert minutes to hours
            result["lifetime"] = value / 60
        elif attr_id == ATTR_MASS_TOTAL:
            result["mass_total"] = int(value)
        elif attr_id == ATTR_MASS_REGEN:
            result["mass_regen"] = int(value)
        elif attr_id == ATTR_MASS_JUMP_MAX:
            result["mass_jump_max"] = int(value)
        elif attr_id in ATTR_TARGET_REGIONS:
            result["target_regions"].append(int(value))
        elif attr_id in ATTR_TARGET_CONSTELLATIONS:
            result["target_constellations"].append(int(value))
        elif attr_id in ATTR_TARGET_SYSTEMS:
            result["target_systems"].append(int(value))

    return result


def load_existing_spawns() -> dict[str, list[str] | None]:
    """Load existing wormhole spawn sources from wormholes.yaml."""
    wormholes_path = PRESEED_DIR / "wormholes.yaml"
    if not wormholes_path.exists():
        return {}

    with wormholes_path.open() as f:
        data = yaml.safe_load(f) or {}

    # Map code -> sources list
    return {code: wh_data.get("sources") for code, wh_data in data.items()}


def convert_sources_to_class_ids(sources: list[str] | None) -> list[int] | None:
    """Convert source strings to class IDs."""
    if sources is None:
        return None

    class_ids = []
    for source in sources:
        if source in SOURCE_TO_CLASS_ID:
            class_ids.append(SOURCE_TO_CLASS_ID[source])
        else:
            # Try to parse as c1-c6 pattern
            click.echo(f"  Warning: Unknown source '{source}'", err=True)
    return sorted(class_ids) if class_ids else None


@collect.command()
@click.option("--user-agent", envvar="LINKED_ESI_USER_AGENT", required=True)
async def wormholes(user_agent: str) -> None:
    """Collect wormhole type data from ESI."""
    # Load existing spawn data for source mappings
    existing_spawns = load_existing_spawns()
    click.echo(f"Loaded {len(existing_spawns)} existing wormhole spawn mappings")

    async with ESIClient(user_agent) as client:
        # Get all wormhole type IDs from group 988
        click.echo("Fetching wormhole group...")
        wh_group = await client.get_group(WORMHOLE_GROUP_ID)
        type_ids = [t for t in wh_group.types if t not in SKIP_TYPE_IDS]
        click.echo(f"Found {len(type_ids)} wormhole types (skipped {len(SKIP_TYPE_IDS)} invalid)")

        # Fetch all type details
        type_list = await fetch_with_rate_limit(type_ids, client.get_type, "wormhole types")

    # First pass: group types by code and collect their data
    code_to_types: dict[str, list[tuple[int, dict]]] = {}

    for wh_type in type_list:
        type_id = wh_type.type_id
        name = wh_type.name

        # Extract wormhole code from name (e.g., "Wormhole X450" -> "X450")
        if name.startswith("Wormhole "):
            code = name[9:]
        else:
            code = name
            click.echo(f"  Warning: Unexpected name format '{name}' for type {type_id}", err=True)

        # Parse dogma attributes
        dogma_info = parse_wormhole_dogma(wh_type.dogma_attributes)

        if code not in code_to_types:
            code_to_types[code] = []
        code_to_types[code].append((type_id, dogma_info))

    # Second pass: merge duplicates by code, using first type ID as primary
    wormhole_info: dict[int, dict] = {}
    wormhole_spawns: dict[int, dict] = {}

    for code, type_data_list in code_to_types.items():
        # Sort by type_id to ensure consistent primary selection
        type_data_list.sort(key=lambda x: x[0])

        primary_type_id, primary_dogma = type_data_list[0]
        alt_type_ids = [t[0] for t in type_data_list[1:]]

        # Merge target lists from all type IDs
        merged_regions = set(primary_dogma.get("target_regions") or [])
        merged_constellations = set(primary_dogma.get("target_constellations") or [])
        merged_systems = set(primary_dogma.get("target_systems") or [])

        # Check for conflicts and merge targets from alternates
        for alt_type_id, alt_dogma in type_data_list[1:]:
            for field in ["mass_total", "mass_jump_max", "mass_regen", "lifetime"]:
                if primary_dogma[field] != alt_dogma[field]:
                    click.echo(
                        f"  Warning: {field} differs for {code}: "
                        f"type {primary_type_id}={primary_dogma[field]} vs "
                        f"type {alt_type_id}={alt_dogma[field]}",
                        err=True,
                    )
            merged_regions.update(alt_dogma.get("target_regions") or [])
            merged_constellations.update(alt_dogma.get("target_constellations") or [])
            merged_systems.update(alt_dogma.get("target_systems") or [])

        if len(type_data_list) > 1:
            click.echo(f"  Note: Code '{code}' merged {len(type_data_list)} type IDs under {primary_type_id}")

        # Build merged info entry
        info_entry = {
            "code": code,
            "lifetime": primary_dogma["lifetime"],
            "target_class": primary_dogma["target_class"],
            "mass_total": primary_dogma["mass_total"],
            "mass_jump_max": primary_dogma["mass_jump_max"],
            "mass_regen": primary_dogma["mass_regen"],
            "target_regions": sorted(merged_regions),
            "target_constellations": sorted(merged_constellations),
            "target_systems": sorted(merged_systems),
        }
        if alt_type_ids:
            info_entry["alt_type_ids"] = alt_type_ids

        wormhole_info[primary_type_id] = info_entry

        # Build spawns entry from existing data
        sources = existing_spawns.get(code)
        wormhole_spawns[primary_type_id] = {
            "sources": convert_sources_to_class_ids(sources),
        }

    # Report wormholes in ESI but not in existing spawns
    esi_codes = set(code_to_types.keys())
    existing_codes = set(existing_spawns.keys())
    new_codes = esi_codes - existing_codes
    missing_codes = existing_codes - esi_codes

    if new_codes:
        click.echo(f"  New wormhole codes from ESI (not in existing spawns): {sorted(new_codes)}")
    if missing_codes:
        click.echo(f"  Existing codes not found in ESI: {sorted(missing_codes)}")

    # Write wormhole_info.yaml
    info_path = PRESEED_DIR / "wormhole_info.yaml"
    with info_path.open("w") as f:
        yaml.safe_dump(wormhole_info, f, sort_keys=True, allow_unicode=True)
    click.echo(f"Wrote {len(wormhole_info)} wormhole entries to {info_path}")

    # Write wormhole_spawns.yaml
    spawns_path = PRESEED_DIR / "wormhole_spawns.yaml"
    with spawns_path.open("w") as f:
        yaml.safe_dump(wormhole_spawns, f, sort_keys=True, allow_unicode=True)
    click.echo(f"Wrote {len(wormhole_spawns)} wormhole spawns to {spawns_path}")


@collect.command("all")
@click.option("--user-agent", envvar="LINKED_ESI_USER_AGENT", required=True)
async def import_all(user_agent: str) -> None:
    """Collect all static data (regions, constellations, systems, wormholes)."""
    # Load existing spawn data for wormhole source mappings
    existing_spawns = load_existing_spawns()

    async with ESIClient(user_agent) as client:
        # Regions
        region_ids = await client.get_regions()
        region_list = await fetch_with_rate_limit(region_ids, client.get_region, "regions")
        region_list.sort(key=lambda r: r.region_id)

        # Constellations
        constellation_ids = await client.get_constellations()
        constellation_list = await fetch_with_rate_limit(constellation_ids, client.get_constellation, "constellations")
        constellation_list.sort(key=lambda c: c.constellation_id)

        # Systems
        system_ids = await client.get_systems()
        system_list = await fetch_with_rate_limit(system_ids, client.get_system, "systems")
        system_list.sort(key=lambda s: s.system_id)

        # Wormholes
        wh_group = await client.get_group(WORMHOLE_GROUP_ID)
        wh_type_ids = [t for t in wh_group.types if t not in SKIP_TYPE_IDS]
        wh_type_list = await fetch_with_rate_limit(wh_type_ids, client.get_type, "wormhole types")

    # Write region/constellation/system files
    for name, items in [
        ("regions", region_list),
        ("constellations", constellation_list),
        ("systems", system_list),
    ]:
        data = [struct_to_dict(item) for item in items]
        output_path = STATIC_DIR / f"{name}.yaml"
        with output_path.open("w") as f:
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
        click.echo(f"Wrote {len(data)} {name} to {output_path}")

    # Process wormhole types - group by code first
    code_to_types: dict[str, list[tuple[int, dict]]] = {}
    for wh_type in wh_type_list:
        type_id = wh_type.type_id
        name = wh_type.name
        code = name[9:] if name.startswith("Wormhole ") else name
        dogma_info = parse_wormhole_dogma(wh_type.dogma_attributes)
        if code not in code_to_types:
            code_to_types[code] = []
        code_to_types[code].append((type_id, dogma_info))

    # Merge duplicates by code
    wormhole_info: dict[int, dict] = {}
    wormhole_spawns: dict[int, dict] = {}

    for code, type_data_list in code_to_types.items():
        type_data_list.sort(key=lambda x: x[0])
        primary_type_id, primary_dogma = type_data_list[0]
        alt_type_ids = [t[0] for t in type_data_list[1:]]

        merged_regions = set(primary_dogma.get("target_regions") or [])
        merged_constellations = set(primary_dogma.get("target_constellations") or [])
        merged_systems = set(primary_dogma.get("target_systems") or [])

        for _, alt_dogma in type_data_list[1:]:
            merged_regions.update(alt_dogma.get("target_regions") or [])
            merged_constellations.update(alt_dogma.get("target_constellations") or [])
            merged_systems.update(alt_dogma.get("target_systems") or [])

        info_entry = {
            "code": code,
            "lifetime": primary_dogma["lifetime"],
            "target_class": primary_dogma["target_class"],
            "mass_total": primary_dogma["mass_total"],
            "mass_jump_max": primary_dogma["mass_jump_max"],
            "mass_regen": primary_dogma["mass_regen"],
            "target_regions": sorted(merged_regions),
            "target_constellations": sorted(merged_constellations),
            "target_systems": sorted(merged_systems),
        }
        if alt_type_ids:
            info_entry["alt_type_ids"] = alt_type_ids

        wormhole_info[primary_type_id] = info_entry
        sources = existing_spawns.get(code)
        wormhole_spawns[primary_type_id] = {"sources": convert_sources_to_class_ids(sources)}

    info_path = PRESEED_DIR / "wormhole_info.yaml"
    with info_path.open("w") as f:
        yaml.safe_dump(wormhole_info, f, sort_keys=True, allow_unicode=True)
    click.echo(f"Wrote {len(wormhole_info)} wormhole entries to {info_path}")

    spawns_path = PRESEED_DIR / "wormhole_spawns.yaml"
    with spawns_path.open("w") as f:
        yaml.safe_dump(wormhole_spawns, f, sort_keys=True, allow_unicode=True)
    click.echo(f"Wrote {len(wormhole_spawns)} wormhole spawns to {spawns_path}")
