"""EVE server status models."""

from __future__ import annotations

import msgspec


class ServerStatus(msgspec.Struct):
    """EVE Online server status from ESI."""

    players: int
    server_version: str
    start_time: str
    vip: bool | None = None
