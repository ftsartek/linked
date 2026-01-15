"""Cron job commands for automated lifecycle management."""

from __future__ import annotations

import asyncclick as click
import valkey.asyncio as valkey
from litestar.channels import ChannelsPlugin
from litestar.channels.backends.redis import RedisChannelsStreamBackend
from sqlspec.adapters.asyncpg.driver import AsyncpgDriver

from config.settings import Settings
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
from services.lifecycle import (
    DEFAULT_SIGNATURE_EXPIRY_DAYS,
    LifecycleResult,
    SignatureLifecycleResult,
    expire_old_signatures,
    update_link_lifetimes,
)


async def _create_event_publisher(settings: Settings) -> EventPublisher:
    """Create an event publisher for cron context."""
    valkey_client = valkey.from_url(settings.valkey.event_url, decode_responses=False)
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


def _print_lifecycle_results(
    link_result: LifecycleResult,
    sig_result: SignatureLifecycleResult,
    signature_expiry_days: int,
    dry_run: bool,
    verbose: bool,
) -> None:
    """Print lifecycle command results."""
    if dry_run:
        click.echo("[lifecycle] DRY RUN - no changes made")

    _print_link_lifecycle_results(link_result, dry_run, verbose)
    _print_signature_lifecycle_results(link_result, sig_result, signature_expiry_days, dry_run, verbose)

    # No changes summary
    total_changes = (
        link_result.updated_count
        + link_result.deleted_count
        + link_result.cascade_deleted_signature_count
        + sig_result.expired_count
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
    """Update link lifetime statuses, soft-delete expired links and signatures.

    This command should be run every 2 minutes via cron.

    Links are soft-deleted when they reach end-of-life based on wormhole lifetime.
    Signatures are soft-deleted after --signature-expiry-days (default 7 days).
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

    _print_lifecycle_results(link_result, sig_result, signature_expiry_days, dry_run, verbose)


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
