"""Valkey dependency providers for map routes."""

from __future__ import annotations

from functools import lru_cache

from valkey import asyncio as valkey

from config import get_settings


@lru_cache
def get_valkey_client() -> valkey.Valkey:
    """Get a Valkey async client for event queues.

    This is separate from the session store to avoid conflicts.

    Returns:
        Valkey async client.
    """
    settings = get_settings()
    # Use database 1 for events (sessions use database 0)
    url = settings.valkey_url.replace("/0", "/1")
    return valkey.from_url(url, decode_responses=False)


def provide_valkey_client() -> valkey.Valkey:
    """Provide Valkey client for dependency injection.

    Returns:
        Valkey async client.
    """
    return get_valkey_client()
