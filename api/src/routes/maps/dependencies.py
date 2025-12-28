"""Dataclasses and types for map routes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from litestar.dto import DataclassDTO, DTOConfig

from utils.effects import apply_class_multiplier


@dataclass
class MapInfo:
    """Map information for API responses."""

    id: UUID
    owner_id: UUID
    name: str
    description: str | None
    is_public: bool
    date_created: datetime
    date_updated: datetime


@dataclass
class EnrichedNodeInfo:
    """Enriched node information for API responses."""

    id: UUID
    pos_x: float
    pos_y: float
    system_id: int
    system_name: str
    constellation_id: int | None
    constellation_name: str | None
    region_id: int | None
    region_name: str | None
    security_status: float | None
    security_class: str | None
    wh_class: int | None
    wh_effect_name: str | None
    raw_buffs: list[dict] | None
    raw_debuffs: list[dict] | None

    @property
    def wh_effect_buffs(self) -> list[dict] | None:
        """Buffs with wormhole class multiplier applied."""
        return apply_class_multiplier(self.raw_buffs, self.wh_class)

    @property
    def wh_effect_debuffs(self) -> list[dict] | None:
        """Debuffs with wormhole class multiplier applied."""
        return apply_class_multiplier(self.raw_debuffs, self.wh_class)


@dataclass
class EnrichedNodeInfoResponse:
    id: UUID
    pos_x: float
    pos_y: float
    system_id: int
    system_name: str
    constellation_id: int | None
    constellation_name: str | None
    region_id: int | None
    region_name: str | None
    security_status: float | None
    security_class: str | None
    wh_class: int | None
    wh_effect_name: str | None
    wh_effect_buffs: list[dict] | None
    wh_effect_debuffs: list[dict] | None

    @classmethod
    def from_origin(cls, origin: EnrichedNodeInfo) -> EnrichedNodeInfoResponse:
        return EnrichedNodeInfoResponse(
            id=origin.id,
            pos_x=origin.pos_x,
            pos_y=origin.pos_y,
            system_id=origin.system_id,
            system_name=origin.system_name,
            constellation_id=origin.constellation_id,
            constellation_name=origin.constellation_name,
            region_id=origin.region_id,
            region_name=origin.region_name,
            security_status=origin.security_status,
            security_class=origin.security_class,
            wh_class=origin.wh_class,
            wh_effect_name=origin.wh_effect_name,
            wh_effect_buffs=origin.wh_effect_buffs,
            wh_effect_debuffs=origin.wh_effect_debuffs,
        )


@dataclass
class EnrichedLinkInfo:
    """Enriched link information for API responses."""

    id: UUID
    source_node_id: UUID
    target_node_id: UUID
    wormhole_code: str | None
    wormhole_mass_total: int | None
    wormhole_mass_jump_max: int | None
    wormhole_mass_regen: int | None
    wormhole_lifetime: int | None
    wormhole_is_static: bool | None
    lifetime_status: str
    date_lifetime_updated: datetime
    mass_usage: str
    date_mass_updated: datetime


@dataclass
class CharacterContext:
    """Character context for access checks."""

    user_id: UUID
    corporation_id: int | None
    alliance_id: int | None


@dataclass
class MapDetailResponse:
    """Full map with nodes and links."""

    map: MapInfo
    nodes: list[EnrichedNodeInfoResponse]
    links: list[EnrichedLinkInfo]


@dataclass
class MapListResponse:
    """List of maps."""

    maps: list[MapInfo]


@dataclass
class UserCharacter:
    """User character info for context lookups."""

    corporation_id: int | None
    alliance_id: int | None


@dataclass
class CreateMapRequest:
    """Request body for creating a map."""

    name: str
    description: str | None = None
    is_public: bool = False


@dataclass
class UpdateMapRequest:
    """Request body for updating a map."""

    name: str | None = None
    description: str | None = None
    is_public: bool | None = None


@dataclass
class AddUserAccessRequest:
    """Request body for adding user access."""

    user_id: UUID
    role: str = "viewer"


@dataclass
class AddCorporationAccessRequest:
    """Request body for adding corporation access."""

    corporation_id: int
    role: str = "viewer"


@dataclass
class AddAllianceAccessRequest:
    """Request body for adding alliance access."""

    alliance_id: int
    role: str = "viewer"
