from __future__ import annotations

from litestar import Controller, get
from litestar.di import Provide

from api.auth.guards import require_auth
from routes.universe.dependencies import (
    SystemSearchResponse,
    WormholeSearchResponse,
)
from routes.universe.service import (
    UniverseService,
    provide_universe_service,
)


class UniverseController(Controller):
    """Universe search endpoints."""

    path = "/universe"
    guards = [require_auth]
    dependencies = {"universe_service": Provide(provide_universe_service, sync_to_thread=False)}

    @get("/systems")
    async def search_systems(
        self,
        universe_service: UniverseService,
        q: str,
    ) -> SystemSearchResponse:
        """Search systems by name."""
        systems = await universe_service.search_systems(q)
        return SystemSearchResponse(systems=systems)

    @get("/wormholes")
    async def search_wormholes(
        self,
        universe_service: UniverseService,
        q: str,
        target_class: int | None = None,
        source: int | None = None,
    ) -> WormholeSearchResponse:
        """Search wormholes by code with optional target_class/source filters."""
        wormholes = await universe_service.search_wormholes(q, target_class, source)
        return WormholeSearchResponse(wormholes=wormholes)
