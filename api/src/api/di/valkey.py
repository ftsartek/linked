from __future__ import annotations

import valkey.asyncio as valkey
from litestar.stores.valkey import ValkeyStore
from valkey.asyncio import Valkey

from config import get_settings


def get_root_store() -> ValkeyStore:
    """Create the root Valkey store."""
    settings = get_settings()
    return ValkeyStore.with_client(url=settings.valkey.session_url)


def get_sessions_store() -> ValkeyStore:
    """Create the sessions store (namespaced under root)."""
    return get_root_store().with_namespace("sessions")


def get_rl_store() -> ValkeyStore:
    """Create the rate limit store (namespaced under root)."""
    return get_root_store().with_namespace("rate_limit")


def get_routes_store() -> ValkeyStore:
    """Create the routes store (namespaced under root)."""
    return get_root_store().with_namespace("routes")


async def provide_valkey_client() -> Valkey:
    """Provide a raw Valkey client for event queues.

    Uses valkey_event_db for event storage (separate from sessions).
    """
    settings = get_settings()
    return valkey.from_url(settings.valkey.event_url, decode_responses=False)
