from __future__ import annotations

from litestar import Controller, get
from litestar.di import Provide
from litestar.exceptions import NotFoundException

from routes.reference.dependencies import (
    WormholeTypeDetail,
    WormholeTypeDetailDTO,
    WormholeTypeSummary,
    WormholeTypeSummaryDTO,
)
from routes.reference.service import ReferenceService, provide_reference_service


class ReferenceController(Controller):
    """Public reference data endpoints."""

    path = "/reference"
    tags = ["Reference"]
    dependencies = {
        "reference_service": Provide(provide_reference_service),
    }

    @get("/wormholes", return_dto=WormholeTypeSummaryDTO, cache=86400)
    async def list_wormholes(
        self,
        reference_service: ReferenceService,
    ) -> list[WormholeTypeSummary]:
        """List all wormhole types.

        Returns a lightweight summary of each wormhole type suitable for
        table display. Response is cached for 24 hours as wormhole data
        is static.
        """
        return await reference_service.list_wormholes()

    @get("/wormholes/{wormhole_id:int}", return_dto=WormholeTypeDetailDTO, cache=86400)
    async def get_wormhole(
        self,
        reference_service: ReferenceService,
        wormhole_id: int,
    ) -> WormholeTypeDetail:
        """Get detailed information for a specific wormhole type.

        Returns full details including human-readable class names,
        lifetime, and mass properties. Response is cached for 24 hours
        as wormhole data is static.
        """
        wormhole = await reference_service.get_wormhole(wormhole_id)
        if wormhole is None:
            raise NotFoundException(f"Wormhole type {wormhole_id} not found")
        return wormhole
