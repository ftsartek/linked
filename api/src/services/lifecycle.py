"""Link and signature lifecycle management service.

Provides functions for updating link lifetime statuses, soft-deleting expired links,
expiring old signatures, and cascading signature deletion when links are deleted.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlspec.adapters.asyncpg.driver import AsyncpgDriver

from routes.maps.dependencies import DeleteNoteResponse, DeleteSignatureResponse, EnrichedLinkInfo
from utils.enums import LifetimeStatus
from utils.wormhole_status import (
    DEFAULT_LIFETIME_HOURS,
    calculate_lifetime_status,
    estimate_eol_time,
)

if TYPE_CHECKING:
    from routes.maps.publisher import EventPublisher

# SQL Queries
GET_ACTIVE_LINKS_WITH_WORMHOLE = """
SELECT
    l.id,
    l.map_id,
    l.lifetime_status,
    l.date_lifetime_updated,
    l.date_created,
    w.lifetime AS wormhole_lifetime
FROM link l
LEFT JOIN wormhole w ON l.wormhole_id = w.id
WHERE l.date_deleted IS NULL;
"""

UPDATE_LINK_LIFETIME_STATUS = """
UPDATE link
SET lifetime_status = $2, date_lifetime_updated = $3, date_updated = NOW()
WHERE id = $1
RETURNING id;
"""

SOFT_DELETE_LINK = """
UPDATE link
SET date_deleted = $2, date_updated = $2
WHERE id = $1 AND date_deleted IS NULL
RETURNING id;
"""

GET_LINK_ENRICHED = """
SELECT
    l.id, l.source_node_id, l.target_node_id,
    w.code AS wormhole_code,
    w.mass_total AS wormhole_mass_total,
    w.mass_jump_max AS wormhole_mass_jump_max,
    w.mass_regen AS wormhole_mass_regen,
    w.lifetime AS wormhole_lifetime,
    l.lifetime_status, l.date_lifetime_updated,
    l.mass_usage, l.date_mass_updated
FROM link l
LEFT JOIN wormhole w ON l.wormhole_id = w.id
WHERE l.id = $1 AND l.date_deleted IS NULL;
"""

# Signature lifecycle queries
GET_EXPIRED_SIGNATURES = """
SELECT id, map_id, node_id
FROM signature
WHERE date_deleted IS NULL AND date_created < $1;
"""

SOFT_DELETE_SIGNATURE = """
UPDATE signature
SET date_deleted = $2, date_updated = $2
WHERE id = $1 AND date_deleted IS NULL
RETURNING id;
"""

SOFT_DELETE_SIGNATURES_BY_LINK = """
UPDATE signature
SET date_deleted = $2, date_updated = $2
WHERE link_id = $1 AND date_deleted IS NULL
RETURNING id, map_id;
"""

# Default signature expiry in days
DEFAULT_SIGNATURE_EXPIRY_DAYS = 7

# Note lifecycle queries
GET_EXPIRED_NOTES = """
SELECT id, map_id
FROM note
WHERE date_deleted IS NULL AND date_expires IS NOT NULL AND date_expires < $1;
"""

SOFT_DELETE_NOTE = """
UPDATE note
SET date_deleted = $2, date_updated = $2
WHERE id = $1 AND date_deleted IS NULL
RETURNING id;
"""


@dataclass
class SignatureLifecycleResult:
    """Result of a signature lifecycle operation."""

    expired_count: int = 0
    cascade_deleted_count: int = 0
    expired_ids: list[UUID] = field(default_factory=list)
    cascade_deleted_ids: list[UUID] = field(default_factory=list)
    maps_affected: set[UUID] = field(default_factory=set)


@dataclass
class NoteLifecycleResult:
    """Result of a note lifecycle operation."""

    expired_count: int = 0
    expired_ids: list[UUID] = field(default_factory=list)
    maps_affected: set[UUID] = field(default_factory=set)


@dataclass
class LifecycleResult:
    """Result of a lifecycle update operation."""

    updated_count: int = 0
    deleted_count: int = 0
    cascade_deleted_signature_count: int = 0
    status_counts: dict[str, int] = field(default_factory=dict)
    updated_ids: list[UUID] = field(default_factory=list)
    deleted_ids: list[UUID] = field(default_factory=list)
    cascade_deleted_signature_ids: list[UUID] = field(default_factory=list)
    maps_affected: set[UUID] = field(default_factory=set)


def _get_status_timestamp(link: dict[str, Any]) -> datetime | None:
    """Get the reference timestamp for status calculation."""
    status_timestamp: datetime | None = link["date_lifetime_updated"]
    if status_timestamp is None:
        status_timestamp = link["date_created"]

    if status_timestamp is None:
        return None

    # Ensure timezone awareness
    if status_timestamp.tzinfo is None:
        status_timestamp = status_timestamp.replace(tzinfo=UTC)

    return status_timestamp


def _process_link(
    link: dict[str, Any],
    current_time: datetime,
) -> tuple[LifetimeStatus | None, bool]:
    """Process a single link and determine if it needs update or deletion.

    Returns:
        Tuple of (new_status or None, should_delete)
    """
    current_status = LifetimeStatus(link["lifetime_status"])
    wormhole_lifetime = link["wormhole_lifetime"]

    status_timestamp = _get_status_timestamp(link)
    if status_timestamp is None:
        return None, False

    lifetime_hours = int(wormhole_lifetime) if wormhole_lifetime else None

    # Check if wormhole has expired (should be deleted)
    eol_time = estimate_eol_time(
        lifetime_status=current_status,
        status_timestamp=status_timestamp,
        wormhole_lifetime_hours=lifetime_hours or DEFAULT_LIFETIME_HOURS,
    )

    if eol_time and current_time >= eol_time:
        return None, True

    # Calculate what the status should be now
    calculated_status = calculate_lifetime_status(
        original_status=current_status,
        status_timestamp=status_timestamp,
        wormhole_lifetime_hours=lifetime_hours,
        current_time=current_time,
    )

    if calculated_status != current_status:
        return calculated_status, False

    return None, False


async def _cascade_delete_link_signatures_internal(
    session: AsyncpgDriver,
    link_id: UUID,
    map_id: UUID,
    current_time: datetime,
    dry_run: bool,
    event_publisher: EventPublisher | None,
) -> list[UUID]:
    """Internal helper to cascade delete signatures when a link is deleted.

    This is used by process_map_lifecycle to avoid circular dependencies.
    """
    if dry_run:
        result = await session.select(
            "SELECT id FROM signature WHERE link_id = $1 AND date_deleted IS NULL",
            [link_id],
        )
        return [row["id"] for row in result]

    result = await session.select(SOFT_DELETE_SIGNATURES_BY_LINK, [link_id, current_time])
    deleted_ids = [row["id"] for row in result]

    if event_publisher and deleted_ids:
        for sig_id in deleted_ids:
            await event_publisher.signature_deleted(
                map_id,
                DeleteSignatureResponse(signature_id=sig_id),
                user_id=None,
            )

    return deleted_ids


async def process_map_lifecycle(
    session: AsyncpgDriver,
    map_id: UUID,
    links: list[dict[str, Any]],
    current_time: datetime,
    dry_run: bool,
    event_publisher: EventPublisher | None,
) -> LifecycleResult:
    """Process lifecycle updates for a single map.

    Args:
        session: Database session
        map_id: The map ID being processed
        links: Links belonging to this map
        current_time: Current time for calculations
        dry_run: If True, calculate changes but don't apply them
        event_publisher: Optional event publisher for SSE notifications

    Returns:
        LifecycleResult for this map
    """
    result = LifecycleResult()

    for link in links:
        link_id: UUID = link["id"]
        new_status, should_delete = _process_link(link, current_time)

        if should_delete:
            # Cascade delete signatures associated with this link
            cascade_sig_ids = await _cascade_delete_link_signatures_internal(
                session=session,
                link_id=link_id,
                map_id=map_id,
                current_time=current_time,
                dry_run=dry_run,
                event_publisher=event_publisher,
            )
            result.cascade_deleted_signature_ids.extend(cascade_sig_ids)
            result.cascade_deleted_signature_count += len(cascade_sig_ids)

            if not dry_run:
                await session.execute(SOFT_DELETE_LINK, [link_id, current_time])
                if event_publisher:
                    from routes.maps.dependencies import DeleteLinkResponse

                    await event_publisher.link_deleted(map_id, DeleteLinkResponse(link_id=link_id), user_id=None)
            result.deleted_ids.append(link_id)
            result.deleted_count += 1
            result.maps_affected.add(map_id)

        elif new_status is not None:
            if not dry_run:
                await session.execute(UPDATE_LINK_LIFETIME_STATUS, [link_id, new_status.value, current_time])
                if event_publisher:
                    enriched = await session.select_one(GET_LINK_ENRICHED, link_id, schema_type=EnrichedLinkInfo)
                    if enriched:
                        await event_publisher.link_updated(map_id, enriched, user_id=None)

            result.status_counts[new_status.name] = result.status_counts.get(new_status.name, 0) + 1
            result.updated_ids.append(link_id)
            result.updated_count += 1
            result.maps_affected.add(map_id)

    return result


async def update_link_lifetimes(
    session: AsyncpgDriver,
    current_time: datetime | None = None,
    dry_run: bool = False,
    event_publisher: EventPublisher | None = None,
) -> LifecycleResult:
    """Update lifetime statuses for all active links and soft-delete expired ones.

    Processes links grouped by map_id to enable per-map SSE event publishing.

    Args:
        session: Database session
        current_time: Current time for calculations (defaults to now UTC)
        dry_run: If True, calculate changes but don't apply them
        event_publisher: Optional event publisher for SSE notifications

    Returns:
        LifecycleResult with counts and IDs of updated/deleted links
    """
    if current_time is None:
        current_time = datetime.now(UTC)

    # Fetch all active links and group by map_id
    links = await session.select(GET_ACTIVE_LINKS_WITH_WORMHOLE)

    links_by_map: dict[UUID, list[dict[str, Any]]] = defaultdict(list)
    for link in links:
        links_by_map[link["map_id"]].append(link)

    # Process each map's links
    total_result = LifecycleResult()

    for map_id, map_links in links_by_map.items():
        map_result = await process_map_lifecycle(
            session=session,
            map_id=map_id,
            links=map_links,
            current_time=current_time,
            dry_run=dry_run,
            event_publisher=event_publisher,
        )

        # Merge results
        total_result.updated_count += map_result.updated_count
        total_result.deleted_count += map_result.deleted_count
        total_result.cascade_deleted_signature_count += map_result.cascade_deleted_signature_count
        total_result.updated_ids.extend(map_result.updated_ids)
        total_result.deleted_ids.extend(map_result.deleted_ids)
        total_result.cascade_deleted_signature_ids.extend(map_result.cascade_deleted_signature_ids)
        total_result.maps_affected.update(map_result.maps_affected)
        for status, count in map_result.status_counts.items():
            total_result.status_counts[status] = total_result.status_counts.get(status, 0) + count

    return total_result


async def cascade_delete_link_signatures(
    session: AsyncpgDriver,
    link_id: UUID,
    map_id: UUID,
    current_time: datetime,
    dry_run: bool = False,
    event_publisher: EventPublisher | None = None,
) -> list[UUID]:
    """Soft-delete all signatures associated with a deleted link.

    Args:
        session: Database session
        link_id: The link ID whose signatures should be deleted
        map_id: The map ID for event publishing
        current_time: Current time for deletion timestamp
        dry_run: If True, calculate changes but don't apply them
        event_publisher: Optional event publisher for SSE notifications

    Returns:
        List of deleted signature IDs
    """
    return await _cascade_delete_link_signatures_internal(
        session=session,
        link_id=link_id,
        map_id=map_id,
        current_time=current_time,
        dry_run=dry_run,
        event_publisher=event_publisher,
    )


async def expire_old_signatures(
    session: AsyncpgDriver,
    expiry_days: int = DEFAULT_SIGNATURE_EXPIRY_DAYS,
    current_time: datetime | None = None,
    dry_run: bool = False,
    event_publisher: EventPublisher | None = None,
) -> SignatureLifecycleResult:
    """Soft-delete signatures older than expiry_days based on date_created.

    Args:
        session: Database session
        expiry_days: Days after creation before signatures are soft-deleted
        current_time: Current time for calculations (defaults to now UTC)
        dry_run: If True, calculate changes but don't apply them
        event_publisher: Optional event publisher for SSE notifications

    Returns:
        SignatureLifecycleResult with counts and IDs of expired signatures
    """
    if current_time is None:
        current_time = datetime.now(UTC)

    cutoff = current_time - timedelta(days=expiry_days)
    result = SignatureLifecycleResult()

    # Get all expired signatures
    expired_sigs = await session.select(GET_EXPIRED_SIGNATURES, [cutoff])

    # Group by map_id for event publishing
    sigs_by_map: dict[UUID, list[dict[str, Any]]] = defaultdict(list)
    for sig in expired_sigs:
        sigs_by_map[sig["map_id"]].append(sig)

    for map_id, signatures in sigs_by_map.items():
        for sig in signatures:
            sig_id: UUID = sig["id"]

            if not dry_run:
                await session.execute(SOFT_DELETE_SIGNATURE, [sig_id, current_time])
                if event_publisher:
                    await event_publisher.signature_deleted(
                        map_id,
                        DeleteSignatureResponse(signature_id=sig_id),
                        user_id=None,
                    )

            result.expired_ids.append(sig_id)
            result.expired_count += 1
            result.maps_affected.add(map_id)

    return result


async def expire_notes(
    session: AsyncpgDriver,
    current_time: datetime | None = None,
    dry_run: bool = False,
    event_publisher: EventPublisher | None = None,
) -> NoteLifecycleResult:
    """Soft-delete notes that have passed their expiry date.

    Args:
        session: Database session
        current_time: Current time for calculations (defaults to now UTC)
        dry_run: If True, calculate changes but don't apply them
        event_publisher: Optional event publisher for SSE notifications

    Returns:
        NoteLifecycleResult with counts and IDs of expired notes
    """
    if current_time is None:
        current_time = datetime.now(UTC)

    result = NoteLifecycleResult()

    # Get all expired notes (where date_expires < current_time)
    expired_notes = await session.select(GET_EXPIRED_NOTES, [current_time])

    # Group by map_id for event publishing
    notes_by_map: dict[UUID, list[dict[str, Any]]] = defaultdict(list)
    for note in expired_notes:
        notes_by_map[note["map_id"]].append(note)

    for map_id, notes in notes_by_map.items():
        for note in notes:
            note_id: UUID = note["id"]

            if not dry_run:
                await session.execute(SOFT_DELETE_NOTE, [note_id, current_time])
                if event_publisher:
                    await event_publisher.note_deleted(
                        map_id,
                        DeleteNoteResponse(note_id=note_id),
                        user_id=None,
                    )

            result.expired_ids.append(note_id)
            result.expired_count += 1
            result.maps_affected.add(map_id)

    return result
