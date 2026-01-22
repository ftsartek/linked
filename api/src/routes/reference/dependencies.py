from __future__ import annotations

import msgspec
from litestar.dto.config import DTOConfig
from litestar.dto.msgspec_dto import MsgspecDTO


class WormholeTypeSummary(msgspec.Struct):
    """Lightweight wormhole type for list display."""

    id: int
    code: str
    target_class: int | None
    sources: list[int] | None


class WormholeTypeSummaryDTO(MsgspecDTO[WormholeTypeSummary]):
    """DTO for wormhole type summary."""

    config = DTOConfig()


class WormholeTypeDetail(msgspec.Struct):
    """Full wormhole type details for detail view."""

    id: int
    code: str
    target_class: int | None
    target_name: str
    sources: list[int] | None
    source_names: list[str]
    lifetime: float | None
    mass_total: int | None
    mass_jump_max: int | None
    mass_regen: int | None


class WormholeTypeDetailDTO(MsgspecDTO[WormholeTypeDetail]):
    """DTO for wormhole type detail."""

    config = DTOConfig()
