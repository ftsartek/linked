"""SSE event collection utilities for testing.

Provides async helpers for collecting and asserting on SSE events
from the /maps/{map_id}/events endpoint.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from uuid import UUID

import msgspec
from httpx_sse import aconnect_sse

from routes.maps.events import EventType, MapEvent

if TYPE_CHECKING:
    from httpx import AsyncClient


async def collect_sse_events(
    client: AsyncClient,
    map_id: UUID,
    timeout: float = 1.0,
    max_events: int = 10,
    connected_event: asyncio.Event | None = None,
    last_event_id: str | None = None,
) -> list[MapEvent]:
    """Collect SSE events from the map events endpoint.

    Connects to the SSE endpoint and collects events until timeout
    or max_events is reached.

    Args:
        client: The httpx AsyncClient
        map_id: Map ID to subscribe to
        timeout: Maximum time to wait for events
        max_events: Stop after collecting this many events
        connected_event: Optional event to set once SSE connection is established
        last_event_id: If provided, only receive events after this event ID (filters history)

    Returns:
        List of collected MapEvent objects
    """
    events: list[MapEvent] = []
    url = f"/maps/{map_id}/events"
    params = {"last_event_id": last_event_id} if last_event_id is not None else None

    try:
        async with asyncio.timeout(timeout):
            async with aconnect_sse(client, "GET", url, params=params) as event_source:
                if connected_event:
                    connected_event.set()
                async for sse in event_source.aiter_sse():
                    if sse.data:
                        # All data events should be valid MapEvent JSON - fail loudly if not
                        event = msgspec.json.decode(sse.data, type=MapEvent)
                        events.append(event)
                        if len(events) >= max_events:
                            break
                    # Comment-only events (keepalive, connect) have no data - skip silently
    except TimeoutError:
        pass  # Expected - we collect until timeout

    return events


def find_events_of_type(events: list[MapEvent], event_type: EventType) -> list[MapEvent]:
    """Filter events by type."""
    return [e for e in events if e.event_type == event_type]


def assert_event_published(
    events: list[MapEvent],
    event_type: EventType,
    **data_matches: object,
) -> MapEvent:
    """Assert an event of the given type was published with matching data.

    Args:
        events: List of collected events
        event_type: Expected event type
        **data_matches: Key-value pairs that must match in event.data

    Returns:
        The matching MapEvent

    Raises:
        AssertionError: If no matching event found
    """
    typed_events = find_events_of_type(events, event_type)
    assert len(typed_events) > 0, f"No {event_type} events found. Got: {[e.event_type for e in events]}"

    if not data_matches:
        return typed_events[0]

    for event in typed_events:
        if all(str(event.data.get(k)) == str(v) for k, v in data_matches.items()):
            return event

    raise AssertionError(f"No {event_type} event matching {data_matches}. Got: {[e.data for e in typed_events]}")
