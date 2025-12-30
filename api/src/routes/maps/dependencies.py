"""Dataclasses and types for map routes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from litestar.dto import DataclassDTO, DTOConfig

from utils.class_mapping import SYSTEM_CLASS_MAPPING
from utils.effects import apply_class_multiplier


@dataclass
class MapInfo:
    """Map information for API responses."""

    id: UUID
    owner_id: UUID
    name: str
    description: str | None
    date_created: datetime
    date_updated: datetime
    is_public: bool = False
    edit_access: bool = False


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
    system_class: int | None
    wh_effect_name: str | None
    raw_buffs: dict[str, int | float] | None
    raw_debuffs: dict[str, int | float] | None

    @property
    def wh_effect_buffs(self) -> dict[str, int | float] | None:
        """Buffs with wormhole class multiplier applied."""
        return apply_class_multiplier(self.raw_buffs, self.system_class)

    @property
    def wh_effect_debuffs(self) -> dict[str, int | float] | None:
        """Debuffs with wormhole class multiplier applied."""
        return apply_class_multiplier(self.raw_debuffs, self.system_class)

    @property
    def class_name(self) -> str | None:
        """Name of the system class."""
        if self.system_class is None:
            return None
        return SYSTEM_CLASS_MAPPING.get(self.system_class)


class EnrichedNodeInfoDTO(DataclassDTO[EnrichedNodeInfo]):
    config = DTOConfig(exclude={"raw_buffs", "raw_debuffs", "system_class"})


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
    wormhole_lifetime: float | None
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
    nodes: list[EnrichedNodeInfo]
    links: list[EnrichedLinkInfo]


class MapDetailResponseDTO(DataclassDTO[MapDetailResponse]):
    config = DTOConfig(exclude={"nodes.0.system_class", "nodes.0.raw_buffs", "nodes.0.raw_debuffs"})


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
    read_only: bool = True


@dataclass
class AddCorporationAccessRequest:
    """Request body for adding corporation access."""

    corporation_id: int
    read_only: bool = True


@dataclass
class AddAllianceAccessRequest:
    """Request body for adding alliance access."""

    alliance_id: int
    read_only: bool = True


@dataclass
class CreateNodeRequest:
    """Request body for creating a node."""

    system_id: int
    pos_x: float
    pos_y: float


@dataclass
class CreateLinkRequest:
    """Request body for creating a link."""

    source_node_id: UUID
    target_node_id: UUID
    wormhole_id: int | None = None
