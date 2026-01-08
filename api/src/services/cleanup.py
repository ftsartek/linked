"""Cleanup service for soft-deleted records.

Provides functions for hard-deleting soft-deleted records after a retention period.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlspec.adapters.asyncpg.driver import AsyncpgDriver

# Default retention period in hours
DEFAULT_RETENTION_HOURS = 24

# SQL Queries - delete in FK-safe order
HARD_DELETE_OLD_SIGNATURES = """
DELETE FROM signature
WHERE date_deleted IS NOT NULL AND date_deleted < $1
RETURNING id;
"""

HARD_DELETE_OLD_LINKS = """
DELETE FROM link
WHERE date_deleted IS NOT NULL AND date_deleted < $1
RETURNING id;
"""

HARD_DELETE_OLD_NODES = """
DELETE FROM node
WHERE date_deleted IS NOT NULL AND date_deleted < $1
RETURNING id;
"""

HARD_DELETE_OLD_MAPS = """
DELETE FROM map
WHERE date_deleted IS NOT NULL AND date_deleted < $1
RETURNING id;
"""

# Count queries for dry-run
COUNT_OLD_SIGNATURES = """
SELECT COUNT(*) FROM signature
WHERE date_deleted IS NOT NULL AND date_deleted < $1;
"""

COUNT_OLD_LINKS = """
SELECT COUNT(*) FROM link
WHERE date_deleted IS NOT NULL AND date_deleted < $1;
"""

COUNT_OLD_NODES = """
SELECT COUNT(*) FROM node
WHERE date_deleted IS NOT NULL AND date_deleted < $1;
"""

COUNT_OLD_MAPS = """
SELECT COUNT(*) FROM map
WHERE date_deleted IS NOT NULL AND date_deleted < $1;
"""


@dataclass
class CleanupResult:
    """Result of a cleanup operation."""

    signatures_deleted: int = 0
    links_deleted: int = 0
    nodes_deleted: int = 0
    maps_deleted: int = 0

    @property
    def total(self) -> int:
        """Total number of records deleted."""
        return self.signatures_deleted + self.links_deleted + self.nodes_deleted + self.maps_deleted


async def cleanup_signatures(
    session: AsyncpgDriver,
    retention_hours: int = DEFAULT_RETENTION_HOURS,
    dry_run: bool = False,
    current_time: datetime | None = None,
) -> int:
    """Hard-delete soft-deleted signatures older than retention period.

    Args:
        session: Database session
        retention_hours: Hours to retain soft-deleted records
        dry_run: If True, count but don't delete
        current_time: Current time for calculations (defaults to now UTC)

    Returns:
        Number of signatures deleted (or would be deleted in dry-run)
    """
    if current_time is None:
        current_time = datetime.now(UTC)
    cutoff = current_time - timedelta(hours=retention_hours)

    if dry_run:
        count = await session.select_value(COUNT_OLD_SIGNATURES, [cutoff])
        return int(count) if count else 0

    result = await session.select(HARD_DELETE_OLD_SIGNATURES, [cutoff])
    return len(result)


async def cleanup_links(
    session: AsyncpgDriver,
    retention_hours: int = DEFAULT_RETENTION_HOURS,
    dry_run: bool = False,
    current_time: datetime | None = None,
) -> int:
    """Hard-delete soft-deleted links older than retention period.

    Args:
        session: Database session
        retention_hours: Hours to retain soft-deleted records
        dry_run: If True, count but don't delete
        current_time: Current time for calculations (defaults to now UTC)

    Returns:
        Number of links deleted (or would be deleted in dry-run)
    """
    if current_time is None:
        current_time = datetime.now(UTC)
    cutoff = current_time - timedelta(hours=retention_hours)

    if dry_run:
        count = await session.select_value(COUNT_OLD_LINKS, [cutoff])
        return int(count) if count else 0

    result = await session.select(HARD_DELETE_OLD_LINKS, [cutoff])
    return len(result)


async def cleanup_nodes(
    session: AsyncpgDriver,
    retention_hours: int = DEFAULT_RETENTION_HOURS,
    dry_run: bool = False,
    current_time: datetime | None = None,
) -> int:
    """Hard-delete soft-deleted nodes older than retention period.

    Args:
        session: Database session
        retention_hours: Hours to retain soft-deleted records
        dry_run: If True, count but don't delete
        current_time: Current time for calculations (defaults to now UTC)

    Returns:
        Number of nodes deleted (or would be deleted in dry-run)
    """
    if current_time is None:
        current_time = datetime.now(UTC)
    cutoff = current_time - timedelta(hours=retention_hours)

    if dry_run:
        count = await session.select_value(COUNT_OLD_NODES, [cutoff])
        return int(count) if count else 0

    result = await session.select(HARD_DELETE_OLD_NODES, [cutoff])
    return len(result)


async def cleanup_maps(
    session: AsyncpgDriver,
    retention_hours: int = DEFAULT_RETENTION_HOURS,
    dry_run: bool = False,
    current_time: datetime | None = None,
) -> int:
    """Hard-delete soft-deleted maps older than retention period.

    Args:
        session: Database session
        retention_hours: Hours to retain soft-deleted records
        dry_run: If True, count but don't delete
        current_time: Current time for calculations (defaults to now UTC)

    Returns:
        Number of maps deleted (or would be deleted in dry-run)
    """
    if current_time is None:
        current_time = datetime.now(UTC)
    cutoff = current_time - timedelta(hours=retention_hours)

    if dry_run:
        count = await session.select_value(COUNT_OLD_MAPS, [cutoff])
        return int(count) if count else 0

    result = await session.select(HARD_DELETE_OLD_MAPS, [cutoff])
    return len(result)


async def cleanup_all(
    session: AsyncpgDriver,
    retention_hours: int = DEFAULT_RETENTION_HOURS,
    dry_run: bool = False,
    current_time: datetime | None = None,
) -> CleanupResult:
    """Hard-delete all soft-deleted records in FK-safe order.

    Deletes in order: signatures -> links -> nodes -> maps

    Args:
        session: Database session
        retention_hours: Hours to retain soft-deleted records
        dry_run: If True, count but don't delete
        current_time: Current time for calculations (defaults to now UTC)

    Returns:
        CleanupResult with counts per entity type
    """
    if current_time is None:
        current_time = datetime.now(UTC)

    return CleanupResult(
        signatures_deleted=await cleanup_signatures(session, retention_hours, dry_run, current_time),
        links_deleted=await cleanup_links(session, retention_hours, dry_run, current_time),
        nodes_deleted=await cleanup_nodes(session, retention_hours, dry_run, current_time),
        maps_deleted=await cleanup_maps(session, retention_hours, dry_run, current_time),
    )
