"""Cron job commands for automated lifecycle management."""

from __future__ import annotations

from typing import TYPE_CHECKING

import asyncclick as click
import valkey.asyncio as valkey
from litestar.channels import ChannelsPlugin
from litestar.channels.backends.redis import RedisChannelsStreamBackend
from sqlspec.adapters.asyncpg.driver import AsyncpgDriver

from database import provide_session
from routes.maps.publisher import EventPublisher
from services.cleanup import (
    DEFAULT_RETENTION_HOURS,
    cleanup_all,
    cleanup_links,
    cleanup_maps,
    cleanup_nodes,
    cleanup_signatures,
)
from services.lifecycle import update_link_lifetimes

if TYPE_CHECKING:
    from config.settings import Settings


async def _create_event_publisher(settings: Settings) -> EventPublisher:
    """Create an event publisher for cron context."""
    valkey_client = valkey.from_url(settings.valkey_event_url, decode_responses=False)
    channels_plugin = ChannelsPlugin(
        backend=RedisChannelsStreamBackend(
            history=100,
            redis=valkey_client,
            key_prefix="MAP_EVENTS",
        ),
        arbitrary_channels_allowed=True,
        create_ws_route_handlers=False,
    )
    return EventPublisher(channels_plugin, valkey_client)


@click.group()
def cron() -> None:
    """Automated cron job commands."""
    pass


@cron.command()
@click.option("--verbose", "-v", is_flag=True, help="Show detailed per-link output")
@click.option("--dry-run", is_flag=True, help="Show what would be done without making changes")
@click.pass_obj
async def lifecycle(settings: Settings, verbose: bool, dry_run: bool) -> None:
    """Update link lifetime statuses and soft-delete expired links.

    This command should be run every 2 minutes via cron.
    """
    # Only create event publisher if we're actually making changes
    event_publisher = None if dry_run else await _create_event_publisher(settings)

    async with provide_session() as session:
        result = await update_link_lifetimes(session, dry_run=dry_run, event_publisher=event_publisher)

    if dry_run:
        click.echo("[lifecycle] DRY RUN - no changes made")

    if result.updated_count > 0:
        parts = [f"{count} {status}" for status, count in result.status_counts.items() if count > 0]
        action = "Would update" if dry_run else "Updated"
        click.echo(f"[lifecycle] {action} {result.updated_count} links: {', '.join(parts)}")
        if verbose:
            for link_id in result.updated_ids:
                click.echo(f"  {link_id}")

    if result.deleted_count > 0:
        action = "Would soft-delete" if dry_run else "Soft-deleted"
        click.echo(f"[lifecycle] {action} {result.deleted_count} expired links")
        if verbose:
            for link_id in result.deleted_ids:
                click.echo(f"  {link_id}")

    if result.updated_count == 0 and result.deleted_count == 0 and verbose:
        click.echo("[lifecycle] No changes needed")


async def _run_individual_cleanups(
    session: AsyncpgDriver,
    retention_hours: int,
    dry_run: bool,
    verbose: bool,
    flags: dict[str, bool],
) -> None:
    """Run individual cleanup operations based on flags."""
    action = "Would delete" if dry_run else "Deleted"
    total = 0

    if flags["signatures"]:
        count = await cleanup_signatures(session, retention_hours, dry_run)
        total += count
        if count > 0 or verbose:
            click.echo(f"[cleanup] {action} {count} signatures")

    if flags["links"]:
        count = await cleanup_links(session, retention_hours, dry_run)
        total += count
        if count > 0 or verbose:
            click.echo(f"[cleanup] {action} {count} links")

    if flags["nodes"]:
        count = await cleanup_nodes(session, retention_hours, dry_run)
        total += count
        if count > 0 or verbose:
            click.echo(f"[cleanup] {action} {count} nodes")

    if flags["maps"]:
        count = await cleanup_maps(session, retention_hours, dry_run)
        total += count
        if count > 0 or verbose:
            click.echo(f"[cleanup] {action} {count} maps")

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
async def cleanup(
    verbose: bool,
    dry_run: bool,
    retention_hours: int,
    do_all: bool,
    do_maps: bool,
    do_links: bool,
    do_nodes: bool,
    do_signatures: bool,
) -> None:
    """Hard-delete soft-deleted records older than retention period.

    This command should be run hourly (e.g., at minute 40).
    Deletes in FK order: signatures -> links -> nodes -> maps.
    """
    # If no specific flags set, default to --all
    if not any([do_all, do_maps, do_links, do_nodes, do_signatures]):
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
                    f"[cleanup] {action}: {result.signatures_deleted} signatures, "
                    f"{result.links_deleted} links, {result.nodes_deleted} nodes, "
                    f"{result.maps_deleted} maps"
                )
        else:
            flags = {
                "signatures": do_signatures,
                "links": do_links,
                "nodes": do_nodes,
                "maps": do_maps,
            }
            await _run_individual_cleanups(session, retention_hours, dry_run, verbose, flags)
