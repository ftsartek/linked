"""Cron job commands for automated lifecycle management."""

from __future__ import annotations

import asyncclick as click
import valkey.asyncio as valkey
from litestar.channels import ChannelsPlugin
from litestar.channels.backends.redis import RedisChannelsStreamBackend
from sqlspec.adapters.asyncpg.driver import AsyncpgDriver

from config.settings import Settings
from database import provide_session
from esi_client.client import ESIClient
from routes.maps.publisher import EventPublisher
from services.cleanup import (
    DEFAULT_RETENTION_HOURS,
    cleanup_all,
    cleanup_links,
    cleanup_maps,
    cleanup_nodes,
    cleanup_notes,
    cleanup_signatures,
)
from services.lifecycle import (
    DEFAULT_SIGNATURE_EXPIRY_DAYS,
    LifecycleResult,
    NoteLifecycleResult,
    SignatureLifecycleResult,
    expire_notes,
    expire_old_signatures,
    update_link_lifetimes,
)
from services.route_cache import TRADE_HUBS, RouteCacheService
from utils.enums import RouteType
from utils.valkey import EVENT_NAMESPACE


async def _create_event_publisher(settings: Settings) -> EventPublisher:
    """Create an event publisher for cron context."""
    valkey_client = valkey.from_url(settings.valkey.url, namespace=EVENT_NAMESPACE, decode_responses=False)
    channels_plugin = ChannelsPlugin(
        backend=RedisChannelsStreamBackend(
            history=100,
            redis=valkey_client,
            key_prefix=EVENT_NAMESPACE,
        ),
        arbitrary_channels_allowed=True,
        create_ws_route_handlers=False,
    )
    return EventPublisher(channels_plugin, valkey_client)


@click.group()
def cron() -> None:
    """Automated cron job commands."""
    pass


def _print_lifecycle_results(
    link_result: LifecycleResult,
    sig_result: SignatureLifecycleResult,
    note_result: NoteLifecycleResult,
    signature_expiry_days: int,
    dry_run: bool,
    verbose: bool,
) -> None:
    """Print lifecycle command results."""
    if dry_run:
        click.echo("[lifecycle] DRY RUN - no changes made")

    _print_link_lifecycle_results(link_result, dry_run, verbose)
    _print_signature_lifecycle_results(link_result, sig_result, signature_expiry_days, dry_run, verbose)
    _print_note_lifecycle_results(note_result, dry_run, verbose)

    # No changes summary
    total_changes = (
        link_result.updated_count
        + link_result.deleted_count
        + link_result.cascade_deleted_signature_count
        + sig_result.expired_count
        + note_result.expired_count
    )
    if total_changes == 0 and verbose:
        click.echo("[lifecycle] No changes needed")


def _print_link_lifecycle_results(link_result: LifecycleResult, dry_run: bool, verbose: bool) -> None:
    """Print link lifecycle results."""
    # Link updates
    if link_result.updated_count > 0:
        parts = [f"{count} {status}" for status, count in link_result.status_counts.items() if count > 0]
        action = "Would update" if dry_run else "Updated"
        click.echo(f"[lifecycle] {action} {link_result.updated_count} links: {', '.join(parts)}")
        if verbose:
            for link_id in link_result.updated_ids:
                click.echo(f"  {link_id}")

    # Link deletions
    if link_result.deleted_count > 0:
        action = "Would soft-delete" if dry_run else "Soft-deleted"
        click.echo(f"[lifecycle] {action} {link_result.deleted_count} expired links")
        if verbose:
            for link_id in link_result.deleted_ids:
                click.echo(f"  {link_id}")


def _print_signature_lifecycle_results(
    link_result: LifecycleResult,
    sig_result: SignatureLifecycleResult,
    signature_expiry_days: int,
    dry_run: bool,
    verbose: bool,
) -> None:
    """Print signature lifecycle results."""
    # Cascade-deleted signatures (from link deletion)
    if link_result.cascade_deleted_signature_count > 0:
        action = "Would cascade-delete" if dry_run else "Cascade-deleted"
        click.echo(f"[lifecycle] {action} {link_result.cascade_deleted_signature_count} signatures from expired links")
        if verbose:
            for sig_id in link_result.cascade_deleted_signature_ids:
                click.echo(f"  {sig_id}")

    # Expired signatures (age-based)
    if sig_result.expired_count > 0:
        action = "Would soft-delete" if dry_run else "Soft-deleted"
        click.echo(
            f"[lifecycle] {action} {sig_result.expired_count} expired signatures (>{signature_expiry_days} days old)"
        )
        if verbose:
            for sig_id in sig_result.expired_ids:
                click.echo(f"  {sig_id}")


def _print_note_lifecycle_results(
    note_result: NoteLifecycleResult,
    dry_run: bool,
    verbose: bool,
) -> None:
    """Print note lifecycle results."""
    if note_result.expired_count > 0:
        action = "Would soft-delete" if dry_run else "Soft-deleted"
        click.echo(f"[lifecycle] {action} {note_result.expired_count} expired notes")
        if verbose:
            for note_id in note_result.expired_ids:
                click.echo(f"  {note_id}")


@cron.command()
@click.option("--verbose", "-v", is_flag=True, help="Show detailed per-link output")
@click.option("--dry-run", is_flag=True, help="Show what would be done without making changes")
@click.option(
    "--signature-expiry-days",
    default=DEFAULT_SIGNATURE_EXPIRY_DAYS,
    show_default=True,
    help="Days after creation before signatures are soft-deleted",
)
@click.pass_obj
async def lifecycle(settings: Settings, verbose: bool, dry_run: bool, signature_expiry_days: int) -> None:
    """Update link lifetime statuses, soft-delete expired links, signatures, and notes.

    This command should be run every 2 minutes via cron.

    Links are soft-deleted when they reach end-of-life based on wormhole lifetime.
    Signatures are soft-deleted after --signature-expiry-days (default 7 days).
    Notes are soft-deleted when they pass their expiry date.
    When a link is soft-deleted, its associated signatures are also cascade-deleted.
    """
    # Only create event publisher if we're actually making changes
    event_publisher = None if dry_run else await _create_event_publisher(settings)

    async with provide_session() as session:
        # Process link lifecycle (includes cascade deletion of signatures)
        link_result = await update_link_lifetimes(session, dry_run=dry_run, event_publisher=event_publisher)

        # Process signature expiration
        sig_result = await expire_old_signatures(
            session,
            expiry_days=signature_expiry_days,
            dry_run=dry_run,
            event_publisher=event_publisher,
        )

        # Process note expiration
        note_result = await expire_notes(
            session,
            dry_run=dry_run,
            event_publisher=event_publisher,
        )

    _print_lifecycle_results(link_result, sig_result, note_result, signature_expiry_days, dry_run, verbose)


async def _run_individual_cleanups(
    session: AsyncpgDriver,
    retention_hours: int,
    dry_run: bool,
    verbose: bool,
    flags: dict[str, bool],
) -> None:
    """Run individual cleanup operations based on flags."""
    # Define cleanup operations in FK order
    cleanup_ops = [
        ("notes", cleanup_notes),
        ("signatures", cleanup_signatures),
        ("links", cleanup_links),
        ("nodes", cleanup_nodes),
        ("maps", cleanup_maps),
    ]

    action = "Would delete" if dry_run else "Deleted"
    total = 0

    for name, cleanup_fn in cleanup_ops:
        if flags[name]:
            count = await cleanup_fn(session, retention_hours, dry_run)
            total += count
            if count > 0 or verbose:
                click.echo(f"[cleanup] {action} {count} {name}")

    if total == 0 and verbose:
        click.echo("[cleanup] No records to clean up")


@cron.command()
@click.option("--verbose", "-v", is_flag=True, help="Show detailed output")
@click.option("--dry-run", is_flag=True, help="Show what would be done without making changes")
@click.option(
    "--retention-hours",
    default=DEFAULT_RETENTION_HOURS,
    show_default=True,
    help="Hours to retain soft-deleted records",
)
@click.option("--all", "do_all", is_flag=True, help="Cleanup all entity types (default if no flags set)")
@click.option("--maps", "do_maps", is_flag=True, help="Cleanup soft-deleted maps")
@click.option("--links", "do_links", is_flag=True, help="Cleanup soft-deleted links")
@click.option("--nodes", "do_nodes", is_flag=True, help="Cleanup soft-deleted nodes")
@click.option("--signatures", "do_signatures", is_flag=True, help="Cleanup soft-deleted signatures")
@click.option("--notes", "do_notes", is_flag=True, help="Cleanup soft-deleted notes")
async def cleanup(
    verbose: bool,
    dry_run: bool,
    retention_hours: int,
    do_all: bool,
    do_maps: bool,
    do_links: bool,
    do_nodes: bool,
    do_signatures: bool,
    do_notes: bool,
) -> None:
    """Hard-delete soft-deleted records older than retention period.

    This command should be run hourly (e.g., at minute 40).
    Deletes in FK order: notes -> signatures -> links -> nodes -> maps.
    """
    # If no specific flags set, default to --all
    if not any([do_all, do_maps, do_links, do_nodes, do_signatures, do_notes]):
        do_all = True

    if dry_run:
        click.echo("[cleanup] DRY RUN - no changes made")

    if verbose:
        click.echo(f"[cleanup] Retention period: {retention_hours} hours")

    async with provide_session() as session:
        if do_all:
            result = await cleanup_all(session, retention_hours, dry_run)
            if result.total > 0 or verbose:
                action = "Would delete" if dry_run else "Deleted"
                click.echo(
                    f"[cleanup] {action}: {result.notes_deleted} notes, "
                    f"{result.signatures_deleted} signatures, "
                    f"{result.links_deleted} links, {result.nodes_deleted} nodes, "
                    f"{result.maps_deleted} maps"
                )
        else:
            flags = {
                "notes": do_notes,
                "signatures": do_signatures,
                "links": do_links,
                "nodes": do_nodes,
                "maps": do_maps,
            }
            await _run_individual_cleanups(session, retention_hours, dry_run, verbose, flags)


# Query to get all active maps with k-space systems
GET_ACTIVE_MAPS_WITH_KSPACE = """
SELECT DISTINCT m.id, m.name
FROM map m
JOIN node n ON n.map_id = m.id
JOIN system s ON n.system_id = s.id
WHERE m.date_deleted IS NULL
  AND n.date_deleted IS NULL
  AND n.system_id > 0
  AND (s.system_class IS NULL OR s.system_class IN (7, 8, 9));
"""

# Query to get k-space systems for a map
GET_MAP_KSPACE_SYSTEMS = """
SELECT DISTINCT s.id
FROM node n
JOIN system s ON n.system_id = s.id
WHERE n.map_id = $1
  AND n.date_deleted IS NULL
  AND n.system_id > 0
  AND (s.system_class IS NULL OR s.system_class IN (7, 8, 9));
"""


async def _process_map_routes(
    session: AsyncpgDriver,
    esi_client: ESIClient,
    map_row: dict,
    route_type_enum: RouteType,
    include_hubs: bool,
    dry_run: bool,
    verbose: bool,
) -> int:
    """Process route pre-fetching for a single map."""
    map_id = map_row["id"]
    map_name = map_row["name"]

    # Get k-space systems for this map
    systems = await session.select(GET_MAP_KSPACE_SYSTEMS, [map_id])
    system_ids = [row["id"] for row in systems]

    if not system_ids:
        return 0

    if verbose:
        click.echo(f"[prefetch-routes] Map '{map_name}': {len(system_ids)} k-space systems")

    if dry_run:
        destinations = set(system_ids)
        if include_hubs:
            destinations.update(TRADE_HUBS)
        potential_routes = len(system_ids) * len(destinations) - len(system_ids)
        click.echo(f"[prefetch-routes]   Would fetch up to {potential_routes} routes")
        return 0

    route_cache = RouteCacheService(session, esi_client)
    fetched = await route_cache.prefetch_routes_for_systems(
        system_ids=system_ids,
        route_type=route_type_enum,
        include_trade_hubs=include_hubs,
    )

    if fetched > 0 or verbose:
        click.echo(f"[prefetch-routes]   Fetched {fetched} new routes")

    return fetched


@cron.command()
@click.option("--verbose", "-v", is_flag=True, help="Show detailed output")
@click.option("--dry-run", is_flag=True, help="Show what would be done without fetching")
@click.option(
    "--route-type",
    type=click.Choice(["shortest", "secure"]),
    default="shortest",
    show_default=True,
    help="Route type to pre-fetch",
)
@click.option("--include-hubs/--no-hubs", default=True, show_default=True, help="Include routes to trade hubs")
@click.pass_obj
async def prefetch_routes(
    settings: Settings,
    verbose: bool,
    dry_run: bool,
    route_type: str,
    include_hubs: bool,
) -> None:
    """Pre-fetch ESI routes for k-space systems on active maps.

    This command pre-caches ESI route calculations between k-space systems
    on active maps, including routes to major trade hubs (Jita, Amarr,
    Dodixie, Rens, Hek).

    Routes are stored permanently in the database since k-space stargates
    don't change.

    This command can be run periodically (e.g., hourly) to ensure routes
    are cached before users need them.
    """
    route_type_enum = RouteType(route_type)

    if dry_run:
        click.echo("[prefetch-routes] DRY RUN - no routes will be fetched")

    if verbose:
        click.echo(f"[prefetch-routes] Route type: {route_type}")
        click.echo(f"[prefetch-routes] Include trade hubs: {include_hubs}")

    esi_client = ESIClient(settings.esi.user_agent, settings.esi.timeout)

    async with provide_session() as session:
        maps = await session.select(GET_ACTIVE_MAPS_WITH_KSPACE)

        if not maps:
            if verbose:
                click.echo("[prefetch-routes] No active maps with k-space systems found")
            return

        if verbose:
            click.echo(f"[prefetch-routes] Found {len(maps)} active maps with k-space systems")

        total_fetched = 0
        for map_row in maps:
            fetched = await _process_map_routes(
                session, esi_client, map_row, route_type_enum, include_hubs, dry_run, verbose
            )
            total_fetched += fetched

        if not dry_run:
            click.echo(f"[prefetch-routes] Total routes fetched: {total_fetched}")
