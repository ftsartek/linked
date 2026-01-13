"""Map event types and models for SSE event streaming."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

import msgspec


class EventType(StrEnum):
    """Types of map events that can be emitted."""

    NODE_CREATED = "node_created"
    NODE_UPDATED = "node_updated"
    NODE_DELETED = "node_deleted"
    LINK_CREATED = "link_created"
    LINK_UPDATED = "link_updated"
    LINK_DELETED = "link_deleted"
    MAP_UPDATED = "map_updated"
    MAP_DELETED = "map_deleted"
    # Signature events
    SIGNATURE_CREATED = "signature_created"
    SIGNATURE_UPDATED = "signature_updated"
    SIGNATURE_DELETED = "signature_deleted"
    SIGNATURES_BULK_UPDATED = "signatures_bulk_updated"
    # Access control events
    ACCESS_CHARACTER_GRANTED = "access_character_granted"
    ACCESS_CHARACTER_REVOKED = "access_character_revoked"
    ACCESS_CORPORATION_GRANTED = "access_corporation_granted"
    ACCESS_CORPORATION_REVOKED = "access_corporation_revoked"
    ACCESS_ALLIANCE_GRANTED = "access_alliance_granted"
    ACCESS_ALLIANCE_REVOKED = "access_alliance_revoked"
    # Error events
    SYNC_ERROR = "sync_error"


# Event types that indicate access revocation
ACCESS_REVOCATION_TYPES: frozenset[EventType] = frozenset(
    {
        EventType.ACCESS_CHARACTER_REVOKED,
        EventType.ACCESS_CORPORATION_REVOKED,
        EventType.ACCESS_ALLIANCE_REVOKED,
    }
)


class MapEvent(msgspec.Struct):
    """A map event that occurred."""

    event_id: str
    """Unique event identifier (monotonically increasing per map)."""

    event_type: EventType
    """Type of event."""

    map_id: UUID
    """Map that the event occurred on."""

    timestamp: datetime
    """When the event occurred."""

    data: dict[str, Any]
    """Event-specific data payload."""

    user_id: UUID | None = None
    """User who triggered the event, if available."""

    @classmethod
    def node_created(
        cls,
        event_id: str,
        map_id: UUID,
        node_data: dict[str, Any],
        user_id: UUID | None = None,
    ) -> MapEvent:
        """Create a node_created event with full node details."""
        return cls(
            event_id=event_id,
            event_type=EventType.NODE_CREATED,
            map_id=map_id,
            timestamp=datetime.now(UTC),
            data=node_data,
            user_id=user_id,
        )

    @classmethod
    def node_updated(
        cls,
        event_id: str,
        map_id: UUID,
        update_data: dict[str, Any],
        user_id: UUID | None = None,
    ) -> MapEvent:
        """Create a node_updated event.

        For position updates: includes node_id, pos_x, pos_y
        For data updates: includes full updated node details
        """
        return cls(
            event_id=event_id,
            event_type=EventType.NODE_UPDATED,
            map_id=map_id,
            timestamp=datetime.now(UTC),
            data=update_data,
            user_id=user_id,
        )

    @classmethod
    def node_deleted(
        cls,
        event_id: str,
        map_id: UUID,
        node_id: UUID,
        user_id: UUID | None = None,
    ) -> MapEvent:
        """Create a node_deleted event."""
        return cls(
            event_id=event_id,
            event_type=EventType.NODE_DELETED,
            map_id=map_id,
            timestamp=datetime.now(UTC),
            data={
                "node_id": str(node_id),
            },
            user_id=user_id,
        )

    @classmethod
    def link_created(
        cls,
        event_id: str,
        map_id: UUID,
        link_data: dict[str, Any],
        user_id: UUID | None = None,
    ) -> MapEvent:
        """Create a link_created event with full link details."""
        return cls(
            event_id=event_id,
            event_type=EventType.LINK_CREATED,
            map_id=map_id,
            timestamp=datetime.now(UTC),
            data=link_data,
            user_id=user_id,
        )

    @classmethod
    def link_updated(
        cls,
        event_id: str,
        map_id: UUID,
        link_data: dict[str, Any],
        user_id: UUID | None = None,
    ) -> MapEvent:
        """Create a link_updated event with full updated link details."""
        return cls(
            event_id=event_id,
            event_type=EventType.LINK_UPDATED,
            map_id=map_id,
            timestamp=datetime.now(UTC),
            data=link_data,
            user_id=user_id,
        )

    @classmethod
    def link_deleted(
        cls,
        event_id: str,
        map_id: UUID,
        link_id: UUID,
        user_id: UUID | None = None,
    ) -> MapEvent:
        """Create a link_deleted event."""
        return cls(
            event_id=event_id,
            event_type=EventType.LINK_DELETED,
            map_id=map_id,
            timestamp=datetime.now(UTC),
            data={
                "link_id": str(link_id),
            },
            user_id=user_id,
        )

    @classmethod
    def map_updated(
        cls,
        event_id: str,
        map_id: UUID,
        changes: dict[str, Any],
        user_id: UUID | None = None,
    ) -> MapEvent:
        """Create a map_updated event."""
        return cls(
            event_id=event_id,
            event_type=EventType.MAP_UPDATED,
            map_id=map_id,
            timestamp=datetime.now(UTC),
            data={
                "changes": changes,
            },
            user_id=user_id,
        )

    @classmethod
    def map_deleted(
        cls,
        event_id: str,
        map_id: UUID,
        deleted_node_ids: list[UUID],
        deleted_link_ids: list[UUID],
        user_id: UUID | None = None,
    ) -> MapEvent:
        """Create a map_deleted event."""
        return cls(
            event_id=event_id,
            event_type=EventType.MAP_DELETED,
            map_id=map_id,
            timestamp=datetime.now(UTC),
            data={
                "deleted_node_ids": [str(n) for n in deleted_node_ids],
                "deleted_link_ids": [str(link) for link in deleted_link_ids],
            },
            user_id=user_id,
        )

    @classmethod
    def access_character_granted(
        cls,
        event_id: str,
        map_id: UUID,
        character_id: int,
        read_only: bool,
        user_id: UUID | None = None,
    ) -> MapEvent:
        """Create an access_character_granted event."""
        return cls(
            event_id=event_id,
            event_type=EventType.ACCESS_CHARACTER_GRANTED,
            map_id=map_id,
            timestamp=datetime.now(UTC),
            data={
                "character_id": character_id,
                "read_only": read_only,
            },
            user_id=user_id,
        )

    @classmethod
    def access_character_revoked(
        cls,
        event_id: str,
        map_id: UUID,
        character_id: int,
        user_id: UUID | None = None,
    ) -> MapEvent:
        """Create an access_character_revoked event."""
        return cls(
            event_id=event_id,
            event_type=EventType.ACCESS_CHARACTER_REVOKED,
            map_id=map_id,
            timestamp=datetime.now(UTC),
            data={
                "character_id": character_id,
            },
            user_id=user_id,
        )

    @classmethod
    def access_corporation_granted(
        cls,
        event_id: str,
        map_id: UUID,
        corporation_id: int,
        read_only: bool,
        user_id: UUID | None = None,
    ) -> MapEvent:
        """Create an access_corporation_granted event."""
        return cls(
            event_id=event_id,
            event_type=EventType.ACCESS_CORPORATION_GRANTED,
            map_id=map_id,
            timestamp=datetime.now(UTC),
            data={
                "corporation_id": corporation_id,
                "read_only": read_only,
            },
            user_id=user_id,
        )

    @classmethod
    def access_corporation_revoked(
        cls,
        event_id: str,
        map_id: UUID,
        corporation_id: int,
        user_id: UUID | None = None,
    ) -> MapEvent:
        """Create an access_corporation_revoked event."""
        return cls(
            event_id=event_id,
            event_type=EventType.ACCESS_CORPORATION_REVOKED,
            map_id=map_id,
            timestamp=datetime.now(UTC),
            data={
                "corporation_id": corporation_id,
            },
            user_id=user_id,
        )

    @classmethod
    def access_alliance_granted(
        cls,
        event_id: str,
        map_id: UUID,
        alliance_id: int,
        read_only: bool,
        user_id: UUID | None = None,
    ) -> MapEvent:
        """Create an access_alliance_granted event."""
        return cls(
            event_id=event_id,
            event_type=EventType.ACCESS_ALLIANCE_GRANTED,
            map_id=map_id,
            timestamp=datetime.now(UTC),
            data={
                "alliance_id": alliance_id,
                "read_only": read_only,
            },
            user_id=user_id,
        )

    @classmethod
    def access_alliance_revoked(
        cls,
        event_id: str,
        map_id: UUID,
        alliance_id: int,
        user_id: UUID | None = None,
    ) -> MapEvent:
        """Create an access_alliance_revoked event."""
        return cls(
            event_id=event_id,
            event_type=EventType.ACCESS_ALLIANCE_REVOKED,
            map_id=map_id,
            timestamp=datetime.now(UTC),
            data={
                "alliance_id": alliance_id,
            },
            user_id=user_id,
        )

    @classmethod
    def signature_created(
        cls,
        event_id: str,
        map_id: UUID,
        signature_data: dict[str, Any],
        user_id: UUID | None = None,
    ) -> MapEvent:
        """Create a signature_created event with full signature details."""
        return cls(
            event_id=event_id,
            event_type=EventType.SIGNATURE_CREATED,
            map_id=map_id,
            timestamp=datetime.now(UTC),
            data=signature_data,
            user_id=user_id,
        )

    @classmethod
    def signature_updated(
        cls,
        event_id: str,
        map_id: UUID,
        signature_data: dict[str, Any],
        user_id: UUID | None = None,
    ) -> MapEvent:
        """Create a signature_updated event with full updated signature details."""
        return cls(
            event_id=event_id,
            event_type=EventType.SIGNATURE_UPDATED,
            map_id=map_id,
            timestamp=datetime.now(UTC),
            data=signature_data,
            user_id=user_id,
        )

    @classmethod
    def signature_deleted(
        cls,
        event_id: str,
        map_id: UUID,
        signature_id: UUID,
        user_id: UUID | None = None,
    ) -> MapEvent:
        """Create a signature_deleted event."""
        return cls(
            event_id=event_id,
            event_type=EventType.SIGNATURE_DELETED,
            map_id=map_id,
            timestamp=datetime.now(UTC),
            data={
                "signature_id": str(signature_id),
            },
            user_id=user_id,
        )

    @classmethod
    def signatures_bulk_updated(
        cls,
        event_id: str,
        map_id: UUID,
        node_id: UUID,
        created_ids: list[UUID],
        updated_ids: list[UUID],
        deleted_ids: list[UUID],
        user_id: UUID | None = None,
    ) -> MapEvent:
        """Create a signatures_bulk_updated event for paste/sync operations."""
        return cls(
            event_id=event_id,
            event_type=EventType.SIGNATURES_BULK_UPDATED,
            map_id=map_id,
            timestamp=datetime.now(UTC),
            data={
                "node_id": str(node_id),
                "created_ids": [str(s) for s in created_ids],
                "updated_ids": [str(s) for s in updated_ids],
                "deleted_ids": [str(s) for s in deleted_ids],
            },
            user_id=user_id,
        )
