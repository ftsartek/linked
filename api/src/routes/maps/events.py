"""Map event types and models for SSE event streaming."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID

import msgspec


class EventType(str, Enum):
    """Types of map events that can be emitted."""

    NODE_CREATED = "node_created"
    NODE_UPDATED = "node_updated"
    NODE_DELETED = "node_deleted"
    LINK_CREATED = "link_created"
    LINK_UPDATED = "link_updated"
    LINK_DELETED = "link_deleted"
    MAP_UPDATED = "map_updated"
    MAP_DELETED = "map_deleted"


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

    def to_sse_data(self) -> str:
        """Convert event to SSE data format."""
        return json.dumps(
            {
                "event_type": self.event_type.value,
                "map_id": str(self.map_id),
                "timestamp": self.timestamp.isoformat(),
                "data": self.data,
                "user_id": str(self.user_id) if self.user_id else None,
            }
        )

    @classmethod
    def node_created(
        cls,
        event_id: str,
        map_id: UUID,
        node_id: UUID,
        user_id: UUID | None = None,
    ) -> MapEvent:
        """Create a node_created event."""
        return cls(
            event_id=event_id,
            event_type=EventType.NODE_CREATED,
            map_id=map_id,
            timestamp=datetime.now(UTC),
            data={"node_id": str(node_id)},
            user_id=user_id,
        )

    @classmethod
    def node_updated(
        cls,
        event_id: str,
        map_id: UUID,
        node_id: UUID,
        changes: dict[str, Any],
        user_id: UUID | None = None,
    ) -> MapEvent:
        """Create a node_updated event."""
        return cls(
            event_id=event_id,
            event_type=EventType.NODE_UPDATED,
            map_id=map_id,
            timestamp=datetime.now(UTC),
            data={
                "node_id": str(node_id),
                "changes": changes,
            },
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
        link_id: UUID,
        user_id: UUID | None = None,
    ) -> MapEvent:
        """Create a link_created event."""
        return cls(
            event_id=event_id,
            event_type=EventType.LINK_CREATED,
            map_id=map_id,
            timestamp=datetime.now(UTC),
            data={"link_id": str(link_id)},
            user_id=user_id,
        )

    @classmethod
    def link_updated(
        cls,
        event_id: str,
        map_id: UUID,
        link_id: UUID,
        changes: dict[str, Any],
        user_id: UUID | None = None,
    ) -> MapEvent:
        """Create a link_updated event."""
        return cls(
            event_id=event_id,
            event_type=EventType.LINK_UPDATED,
            map_id=map_id,
            timestamp=datetime.now(UTC),
            data={
                "link_id": str(link_id),
                "changes": changes,
            },
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
        user_id: UUID | None = None,
    ) -> MapEvent:
        """Create a map_deleted event."""
        return cls(
            event_id=event_id,
            event_type=EventType.MAP_DELETED,
            map_id=map_id,
            timestamp=datetime.now(UTC),
            data={},
            user_id=user_id,
        )
