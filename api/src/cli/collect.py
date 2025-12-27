import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TypeVar

import asyncclick as click
import msgspec
import yaml

from esi_client import Constellation, ESIClient, Region, System

T = TypeVar("T")

STATIC_DIR = Path(__file__).parent.parent.parent / "static"

# Conservative rate limit: max 20 concurrent requests
MAX_CONCURRENT = 20


async def fetch_with_rate_limit(
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
    done = 0
    for coro in asyncio.as_completed(tasks):
        await coro
        done += 1
        if done % 100 == 0 or done == total:
            click.echo(f"  Progress: {done}/{total}")

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
        region_list = await fetch_with_rate_limit(
            region_ids, client.get_region, "regions"
        )

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
        constellation_list = await fetch_with_rate_limit(
            constellation_ids, client.get_constellation, "constellations"
        )

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
        system_list = await fetch_with_rate_limit(
            system_ids, client.get_system, "systems"
        )

    system_list.sort(key=lambda s: s.system_id)
    data = [struct_to_dict(s) for s in system_list]

    output_path = STATIC_DIR / "systems.yaml"
    with output_path.open("w") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)

    click.echo(f"Wrote {len(data)} systems to {output_path}")


@collect.command()
@click.option("--user-agent", envvar="LINKED_ESI_USER_AGENT", required=True)
async def all(user_agent: str) -> None:
    """Collect all static data (regions, constellations, systems)."""
    async with ESIClient(user_agent) as client:
        # Regions
        region_ids = await client.get_regions()
        region_list = await fetch_with_rate_limit(
            region_ids, client.get_region, "regions"
        )
        region_list.sort(key=lambda r: r.region_id)

        # Constellations
        constellation_ids = await client.get_constellations()
        constellation_list = await fetch_with_rate_limit(
            constellation_ids, client.get_constellation, "constellations"
        )
        constellation_list.sort(key=lambda c: c.constellation_id)

        # Systems
        system_ids = await client.get_systems()
        system_list = await fetch_with_rate_limit(
            system_ids, client.get_system, "systems"
        )
        system_list.sort(key=lambda s: s.system_id)

    # Write all files
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
