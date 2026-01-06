from __future__ import annotations

import asyncio
import io
import zipfile
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import asyncclick as click
import httpx
import msgspec
import yaml

from esi_client import ESIClient
from esi_client.models import DogmaAttribute

STATIC_DIR = Path(__file__).parent.parent.parent / "static"
PRESEED_DIR = STATIC_DIR / "preseed"
CURATED_DIR = PRESEED_DIR / "curated"
SDE_DIR = PRESEED_DIR / "sde"

# SDE download URL
SDE_URL = "https://developers.eveonline.com/static-data/eve-online-static-data-latest-yaml.zip"

# Files to extract from SDE zip (path in zip -> local filename)
SDE_FILES = {
    "sde/fsd/universe/eve/mapRegions.yaml": "mapRegions.yaml",
    "sde/fsd/universe/eve/mapConstellations.yaml": "mapConstellations.yaml",
    "sde/fsd/universe/eve/mapSolarSystems.yaml": "mapSolarSystems.yaml",
}

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

    output_path = PRESEED_DIR / "regions.yaml"
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

    output_path = PRESEED_DIR / "constellations.yaml"
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

    output_path = PRESEED_DIR / "systems.yaml"
    with output_path.open("w") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)

    click.echo(f"Wrote {len(data)} systems to {output_path}")


@collect.command()
async def sde() -> None:
    """Download and extract SDE map data from CCP."""
    await download_sde()


# Wormhole group ID in ESI
WORMHOLE_GROUP_ID = 988

# Type IDs to skip (invalid/test wormholes)
SKIP_TYPE_IDS = {32894, 32895}

# Dogma attribute IDs
ATTR_TARGET_CLASS = 1381
ATTR_LIFETIME = 1382
ATTR_MASS_TOTAL = 1383
ATTR_MASS_REGEN = 1384
ATTR_MASS_JUMP_MAX = 1385
ATTR_TARGET_REGIONS = range(1386, 1395)  # 1386-1394
ATTR_TARGET_CONSTELLATIONS = range(1395, 1404)  # 1395-1403
ATTR_TARGET_SYSTEMS = range(1404, 1413)  # 1404-1412


def _apply_dogma_attribute(result: dict[str, Any], attr_id: int, value: float) -> None:
    """Apply a single dogma attribute to the result dictionary."""
    # Direct attribute mappings (attr_id -> (field_name, transform_fn))
    direct_attrs: dict[int, tuple[str, Callable[[float], Any]]] = {
        ATTR_TARGET_CLASS: ("target_class", int),
        ATTR_LIFETIME: ("lifetime", lambda v: v / 60),  # Convert minutes to hours
        ATTR_MASS_TOTAL: ("mass_total", int),
        ATTR_MASS_REGEN: ("mass_regen", int),
        ATTR_MASS_JUMP_MAX: ("mass_jump_max", int),
    }

    if attr_id in direct_attrs:
        field, transform = direct_attrs[attr_id]
        result[field] = transform(value)
    elif attr_id in ATTR_TARGET_REGIONS:
        result["target_regions"].append(int(value))
    elif attr_id in ATTR_TARGET_CONSTELLATIONS:
        result["target_constellations"].append(int(value))
    elif attr_id in ATTR_TARGET_SYSTEMS:
        result["target_systems"].append(int(value))


def parse_wormhole_dogma(dogma_attributes: list[DogmaAttribute] | None) -> dict[str, Any]:
    """Parse dogma attributes into wormhole info fields."""
    result: dict[str, Any] = {
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
        _apply_dogma_attribute(result, attr.attribute_id, attr.value)

    return result


def load_existing_spawns() -> dict[str, list[int] | None]:
    """Load existing wormhole spawn sources from wormhole_spawns.yaml and wormhole_info.yaml.

    Returns a mapping of wormhole code -> source class IDs.
    """
    spawns_path = CURATED_DIR / "wormhole_spawns.yaml"  # Curated data
    info_path = PRESEED_DIR / "wormhole_info.yaml"  # Generated data

    if not spawns_path.exists() or not info_path.exists():
        return {}

    with spawns_path.open() as f:
        spawns_data = yaml.safe_load(f) or {}

    with info_path.open() as f:
        info_data = yaml.safe_load(f) or {}

    # Build code -> sources mapping by joining spawns (type_id keyed) with info (has code)
    code_to_sources: dict[str, list[int] | None] = {}
    for type_id_key, spawn_info in spawns_data.items():
        type_id = int(type_id_key) if isinstance(type_id_key, str) else type_id_key
        info = info_data.get(type_id) or info_data.get(str(type_id))
        if info and "code" in info:
            code = info["code"]
            code_to_sources[code] = spawn_info.get("sources")

    return code_to_sources


def _group_wormhole_types(type_list: list) -> dict[str, list[tuple[int, dict]]]:
    """Group wormhole types by their code, parsing dogma attributes."""
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

        dogma_info = parse_wormhole_dogma(wh_type.dogma_attributes)

        if code not in code_to_types:
            code_to_types[code] = []
        code_to_types[code].append((type_id, dogma_info))

    return code_to_types


def _merge_wormhole_duplicates(
    code_to_types: dict[str, list[tuple[int, dict]]],
) -> dict[int, dict]:
    """Merge duplicate wormhole types by code, returning wormhole_info dict."""
    wormhole_info: dict[int, dict] = {}

    for code, type_data_list in code_to_types.items():
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

    return wormhole_info


@collect.command()
@click.option("--user-agent", envvar="LINKED_ESI_USER_AGENT", required=True)
async def wormholes(user_agent: str) -> None:
    """Collect wormhole type data from ESI."""
    existing_spawns = load_existing_spawns()
    click.echo(f"Loaded {len(existing_spawns)} existing wormhole spawn mappings")

    async with ESIClient(user_agent) as client:
        click.echo("Fetching wormhole group...")
        wh_group = await client.get_group(WORMHOLE_GROUP_ID)
        type_ids = [t for t in wh_group.types if t not in SKIP_TYPE_IDS]
        click.echo(f"Found {len(type_ids)} wormhole types (skipped {len(SKIP_TYPE_IDS)} invalid)")
        type_list = await fetch_with_rate_limit(type_ids, client.get_type, "wormhole types")

    code_to_types = _group_wormhole_types(type_list)
    wormhole_info = _merge_wormhole_duplicates(code_to_types)

    # Report code discrepancies (compare ESI codes with curated spawns)
    esi_codes = set(code_to_types.keys())
    existing_codes = set(existing_spawns.keys())
    if new_codes := esi_codes - existing_codes:
        click.echo(f"  New wormhole codes from ESI (not in existing spawns): {sorted(new_codes)}")
    if missing_codes := existing_codes - esi_codes:
        click.echo(f"  Existing codes not found in ESI: {sorted(missing_codes)}")

    # Write wormhole_info.yaml (wormhole_spawns.yaml is curated, not generated)
    info_path = PRESEED_DIR / "wormhole_info.yaml"
    with info_path.open("w") as f:
        yaml.safe_dump(wormhole_info, f, sort_keys=True, allow_unicode=True)
    click.echo(f"Wrote {len(wormhole_info)} wormhole entries to {info_path}")


async def download_sde() -> None:
    """Download and extract SDE data (shared logic for sde and all commands)."""
    click.echo(f"Downloading SDE from {SDE_URL}...")

    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(SDE_URL)
        response.raise_for_status()

    click.echo(f"Downloaded {len(response.content) / 1024 / 1024:.1f} MB")

    SDE_DIR.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        all_files = zf.namelist()

        for zip_path, local_name in SDE_FILES.items():
            if zip_path in all_files:
                source_path = zip_path
            else:
                matches = [f for f in all_files if f.endswith(local_name)]
                if not matches:
                    click.echo(f"  Warning: {local_name} not found in archive", err=True)
                    continue
                source_path = matches[0]

            click.echo(f"  Extracting {local_name}...")
            content = zf.read(source_path)
            output_path = SDE_DIR / local_name
            output_path.write_bytes(content)

    click.echo(f"SDE data extracted to {SDE_DIR}")


@collect.command("all")
@click.option("--user-agent", envvar="LINKED_ESI_USER_AGENT", required=True)
async def import_all(user_agent: str) -> None:
    """Collect all static data (SDE, regions, constellations, systems, wormholes)."""
    # Download SDE data first
    await download_sde()

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
        output_path = PRESEED_DIR / f"{name}.yaml"
        with output_path.open("w") as f:
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
        click.echo(f"Wrote {len(data)} {name} to {output_path}")

    # Process wormhole types using shared helpers
    wh_type_list_filtered = [wh for wh in wh_type_list if wh is not None]
    code_to_types = _group_wormhole_types(wh_type_list_filtered)
    wormhole_info = _merge_wormhole_duplicates(code_to_types)

    # Write wormhole_info.yaml (wormhole_spawns.yaml is curated, not generated)
    info_path = PRESEED_DIR / "wormhole_info.yaml"
    with info_path.open("w") as f:
        yaml.safe_dump(wormhole_info, f, sort_keys=True, allow_unicode=True)
    click.echo(f"Wrote {len(wormhole_info)} wormhole entries to {info_path}")
