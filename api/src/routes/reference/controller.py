from __future__ import annotations

from litestar import Controller, get
from litestar.di import Provide
from litestar.exceptions import NotFoundException
from litestar.params import Parameter

from routes.reference.dependencies import (
    WormholeSystemsGrouped,
    WormholeSystemsGroupedDTO,
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

    @get("/systems", return_dto=WormholeSystemsGroupedDTO, cache=86400)
    async def list_wormhole_systems(
        self,
        reference_service: ReferenceService,
        system_classes: list[int] | None = Parameter(query="class", default=None),
        effect_id: int | None = Parameter(query="effect", default=None),
        region_id: int | None = Parameter(query="region", default=None),
        constellation_id: int | None = Parameter(query="constellation", default=None),
        shattered: bool | None = Parameter(query="shattered", default=None),
        static_id: int | None = Parameter(query="static", default=None),
    ) -> WormholeSystemsGrouped:
        """List all wormhole systems grouped by region and constellation.

        Returns wormhole systems (C1-C6, Thera, C13, Drifter wormholes) with
        their statics, effects, and location data, grouped hierarchically
        by region and constellation. Response is cached for 24 hours as
        system data is static.

        Filters:
        - class: Filter by wormhole class(es) (1-6, 12, 13, 14-18), can be repeated
        - effect: Filter by wormhole effect ID
        - region: Filter by region ID
        - constellation: Filter by constellation ID
        - shattered: Filter by shattered status (true/false)
        - static: Filter by static target class (e.g., 7=HS, 8=LS, 9=NS, 1-6=C1-C6)
        """
        return await reference_service.list_wormhole_systems(
            system_classes=system_classes,
            effect_id=effect_id,
            region_id=region_id,
            constellation_id=constellation_id,
            shattered=shattered,
            static_id=static_id,
        )
