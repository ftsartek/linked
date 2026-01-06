from __future__ import annotations

import valkey.asyncio as valkey
from litestar.stores.valkey import ValkeyStore
from valkey.asyncio import Valkey

from config import get_settings

settings = get_settings()


async def provide_valkey_client() -> Valkey:
    """Provide a raw Valkey client for event queues.

    Uses valkey_event_db for event storage (separate from sessions).
    """
    return valkey.from_url(settings.valkey_event_url, decode_responses=False)


# Create root Valkey store and namespaced children
root_store = ValkeyStore.with_client(url=settings.valkey_session_url)
rl_store = root_store.with_namespace("rate_limit")
sessions_store = root_store.with_namespace("sessions")
