"""Event queue manager for map events using Valkey."""

from __future__ import annotations

import json
from typing import AsyncIterator
from uuid import UUID

import msgspec
from valkey import asyncio as valkey

from routes.maps.events import MapEvent


class MapEventQueue:
    """Manages per-map event queues using Valkey.

    Events are stored as JSON strings in a Redis stream for each map.
    This allows for event replay and SSE subscriptions.
    """

    def __init__(self, valkey_client: valkey.Valkey) -> None:
        self.valkey = valkey_client
        self._encoder = msgspec.json.Encoder()
        self._decoder = msgspec.json.Decoder(type=MapEvent)

    def _get_stream_key(self, map_id: UUID) -> str:
        """Get the Valkey stream key for a map's events."""
        return f"map_events:{map_id}"

    def _get_counter_key(self, map_id: UUID) -> str:
        """Get the Valkey key for the event ID counter."""
        return f"map_event_counter:{map_id}"

    async def publish_event(self, event: MapEvent) -> None:
        """Publish an event to the map's event stream.

        Args:
            event: The event to publish.
        """
        stream_key = self._get_stream_key(event.map_id)

        # Store event in stream with the event_id as the Redis stream ID
        # Using XADD with explicit ID allows us to control event IDs
        await self.valkey.xadd(
            stream_key,
            {"data": self._encoder.encode(event)},
            id=event.event_id,
        )

        # Set expiration on the stream (7 days)
        await self.valkey.expire(stream_key, 604800)

    async def get_next_event_id(self, map_id: UUID) -> str:
        """Get the next event ID for a map.

        Uses Redis INCR to generate monotonically increasing IDs.
        Event IDs are in the format: <counter>-0

        Args:
            map_id: The map ID.

        Returns:
            The next event ID string.
        """
        counter_key = self._get_counter_key(map_id)
        counter = await self.valkey.incr(counter_key)

        # Set expiration on counter (7 days)
        await self.valkey.expire(counter_key, 604800)

        # Redis stream IDs are in format: <millisecondsTime>-<sequenceNumber>
        # We use counter as the timestamp portion and 0 as sequence
        return f"{counter}-0"

    async def get_events_since(
        self,
        map_id: UUID,
        last_event_id: str | None = None,
    ) -> list[MapEvent]:
        """Get all events since the given event ID.

        Args:
            map_id: The map ID.
            last_event_id: The last event ID received, or None for all events.

        Returns:
            List of events in order.
        """
        stream_key = self._get_stream_key(map_id)

        # If no last_event_id, start from the beginning
        start_id = last_event_id if last_event_id else "0-0"

        # Read events from the stream
        # Use XREAD with start_id to get all events after that ID
        results = await self.valkey.xrange(stream_key, f"({start_id}", "+")

        events = []
        for event_id, data in results:
            event_json = data[b"data"]
            event = self._decoder.decode(event_json)
            events.append(event)

        return events

    async def stream_events(
        self,
        map_id: UUID,
        last_event_id: str | None = None,
        block_ms: int = 5000,
    ) -> AsyncIterator[MapEvent]:
        """Stream events from a map in real-time.

        This uses Redis XREAD with BLOCK to wait for new events.

        Args:
            map_id: The map ID.
            last_event_id: The last event ID received, or None to start from latest.
            block_ms: How long to block waiting for new events (milliseconds).

        Yields:
            Events as they arrive.
        """
        stream_key = self._get_stream_key(map_id)
        current_id = last_event_id if last_event_id else "$"

        while True:
            # Use XREAD to block until new events arrive
            results = await self.valkey.xread(
                {stream_key: current_id},
                block=block_ms,
                count=10,
            )

            if not results:
                # Timeout occurred, yield control and continue
                continue

            for _stream, events in results:
                for event_id, data in events:
                    event_json = data[b"data"]
                    event = self._decoder.decode(event_json)
                    yield event

                    # Update current_id for next iteration
                    current_id = event_id.decode() if isinstance(event_id, bytes) else event_id

    async def delete_map_events(self, map_id: UUID) -> None:
        """Delete all events for a map.

        Args:
            map_id: The map ID.
        """
        stream_key = self._get_stream_key(map_id)
        counter_key = self._get_counter_key(map_id)

        await self.valkey.delete(stream_key, counter_key)


def provide_event_queue(valkey_client: valkey.Valkey) -> MapEventQueue:
    """Provide MapEventQueue with injected Valkey client.

    Args:
        valkey_client: The Valkey async client.

    Returns:
        MapEventQueue instance.
    """
    return MapEventQueue(valkey_client)
