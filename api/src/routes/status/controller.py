"""EVE server status endpoint."""

from __future__ import annotations

import msgspec
from litestar import Controller, get

from esi_client import ESIClient
from esi_client.exceptions import ESIError


class EVEStatusResponse(msgspec.Struct):
    """EVE server status response."""

    online: bool
    vip: bool = False
    players: int | None = None


class StatusController(Controller):
    """EVE server status endpoints."""

    path = "/status"
    tags = ["Status"]

    @get("/eve", cache=30)
    async def get_eve_status(self, esi_client: ESIClient) -> EVEStatusResponse:
        """Get EVE Online Tranquility server status."""
        try:
            async with esi_client:
                status = await esi_client.get_server_status()
            return EVEStatusResponse(
                online=True,
                vip=status.vip or False,
                players=status.players,
            )
        except ESIError:
            return EVEStatusResponse(online=False, vip=False, players=None)
