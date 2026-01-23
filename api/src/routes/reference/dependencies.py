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


class WormholeSystemStatic(msgspec.Struct):
    """Static wormhole connection for a system."""

    id: int
    code: str
    target_class: int | None
    target_name: str


class WormholeSystemItem(msgspec.Struct):
    """Wormhole system item within a constellation."""

    id: int
    name: str
    system_class: int
    class_name: str
    effect_id: int | None
    effect_name: str | None
    shattered: bool
    statics: list[WormholeSystemStatic]


class WormholeConstellation(msgspec.Struct):
    """Constellation containing wormhole systems."""

    id: int
    name: str
    systems: list[WormholeSystemItem]


class WormholeRegion(msgspec.Struct):
    """Region containing constellations."""

    id: int
    name: str
    constellations: list[WormholeConstellation]


class WormholeSystemsGrouped(msgspec.Struct):
    """Grouped wormhole systems response."""

    regions: list[WormholeRegion]
    total_systems: int


class WormholeSystemsGroupedDTO(MsgspecDTO[WormholeSystemsGrouped]):
    """DTO for grouped wormhole systems."""

    # Need depth 4 for: regions -> constellations -> systems -> statics
    config = DTOConfig(max_nested_depth=4)
