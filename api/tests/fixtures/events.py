"""SSE event collection utilities for test verification."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from uuid import UUID

import msgspec

if TYPE_CHECKING:
    from valkey.asyncio import Valkey

    from routes.maps.events import EventType, MapEvent


class EventCollector:
    """Collects SSE events published to a map channel for verification.

    This subscribes to the same Valkey channel that the app publishes to,
    allowing tests to verify that the correct events are emitted.
    """

    def __init__(self, valkey_client: Valkey, map_id: UUID) -> None:
        self.valkey = valkey_client
        self.map_id = map_id
        self.events: list[MapEvent] = []
        self._pubsub = None

    async def start(self) -> None:
        """Subscribe to the map's event channel."""

        self._pubsub = self.valkey.pubsub()
        channel_name = f"MAP_EVENTS:map:{self.map_id}"
        await self._pubsub.subscribe(channel_name)

    async def stop(self) -> None:
        """Unsubscribe and close the pubsub connection."""
        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.close()

    async def collect(self, timeout: float = 0.5, max_events: int = 100) -> None:
        """Collect any pending events from the channel.

        Args:
            timeout: Maximum time to wait for events (seconds)
            max_events: Maximum number of events to collect
        """
        from routes.maps.events import MapEvent

        if not self._pubsub:
            return

        collected = 0
        start_time = asyncio.get_event_loop().time()

        while collected < max_events:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= timeout:
                break

            remaining = timeout - elapsed
            try:
                message = await asyncio.wait_for(
                    self._pubsub.get_message(ignore_subscribe_messages=True),
                    timeout=min(remaining, 0.1),
                )
                if message and message["type"] == "message":
                    data = message["data"]
                    if isinstance(data, bytes):
                        event = msgspec.json.decode(data, type=MapEvent)
                        self.events.append(event)
                        collected += 1
            except TimeoutError:
                # No message available, continue checking
                continue
            except Exception:
                # Ignore decode errors, etc.
                continue

    def get_events_of_type(self, event_type: EventType) -> list[MapEvent]:
        """Filter collected events by type.

        Args:
            event_type: The event type to filter for

        Returns:
            List of events matching the type
        """
        return [e for e in self.events if e.event_type == event_type]

    def assert_event_published(
        self,
        event_type: EventType,
        **data_matches: object,
    ) -> MapEvent:
        """Assert an event of the given type was published.

        Args:
            event_type: Expected event type
            **data_matches: Optional key-value pairs that must match in event.data

        Returns:
            The matching event

        Raises:
            AssertionError: If no matching event found
        """
        events = self.get_events_of_type(event_type)
        assert len(events) > 0, f"No {event_type} events found. Collected: {[e.event_type for e in self.events]}"

        if data_matches:
            for event in events:
                matches = all(str(event.data.get(key)) == str(value) for key, value in data_matches.items())
                if matches:
                    return event
            raise AssertionError(
                f"No {event_type} event found matching {data_matches}. Events: {[e.data for e in events]}"
            )

        return events[0]

    def assert_no_events(self) -> None:
        """Assert that no events were collected."""
        assert len(self.events) == 0, f"Expected no events but found: {[e.event_type for e in self.events]}"

    def clear(self) -> None:
        """Clear collected events."""
        self.events.clear()
