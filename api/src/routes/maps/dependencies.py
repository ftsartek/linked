"""Msgspec structs and types for map routes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import msgspec
from litestar.dto import DTOConfig
from litestar.dto.msgspec_dto import MsgspecDTO

from utils.class_mapping import SYSTEM_CLASS_MAPPING
from utils.effects import apply_class_multiplier
from utils.enums import EdgeType, RankDir

# Error messages
ERR_MAP_NOT_FOUND = "Map not found"
ERR_MAP_NO_ACCESS = "You do not have access to this map"
ERR_MAP_NO_EDIT_ACCESS = "You do not have edit access to this map"
ERR_MAP_OWNER_ONLY = "Only the map owner can perform this action"
ERR_NODE_NOT_FOUND = "Node not found"
ERR_NODE_LOCKED = "Node is locked"
ERR_LINK_NOT_FOUND = "Link not found"
ERR_LINK_NODE_MISMATCH = "Link not found or node not connected to link"
ERR_SIGNATURE_NOT_FOUND = "Signature not found"


class StaticInfo(msgspec.Struct):
    """Wormhole static information."""

    code: str
    target_class_name: str | None


class CharacterAccessInfo(msgspec.Struct):
    """Character access entry for a map."""

    character_id: int
    character_name: str
    read_only: bool


class CorporationAccessInfo(msgspec.Struct):
    """Corporation access entry for a map."""

    corporation_id: int
    corporation_name: str
    corporation_ticker: str
    read_only: bool


class AllianceAccessInfo(msgspec.Struct):
    """Alliance access entry for a map."""

    alliance_id: int
    alliance_name: str
    alliance_ticker: str
    read_only: bool


class MapAccessResponse(msgspec.Struct):
    """Response containing all access entries for a map."""

    characters: list[CharacterAccessInfo]
    corporations: list[CorporationAccessInfo]
    alliances: list[AllianceAccessInfo]


class MapInfo(msgspec.Struct):
    """Map information for API responses."""

    id: UUID
    owner_id: UUID
    name: str
    description: str | None
    date_created: datetime
    date_updated: datetime
    is_public: bool = False
    public_read_only: bool = True
    edge_type: EdgeType = EdgeType.DEFAULT
    rankdir: RankDir = RankDir.TB
    auto_layout: bool = False
    node_sep: int = 60
    rank_sep: int = 60
    edit_access: bool = False


class EnrichedNodeSourceData(msgspec.Struct):
    """Raw enriched node data from database queries."""

    id: UUID
    pos_x: float
    pos_y: float
    locked: bool
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
    static_codes: list[str] | None = None
    static_target_classes: list[int] | None = None


class EnrichedNodeInfo(msgspec.Struct):
    """Enriched node information for API responses."""

    id: UUID
    pos_x: float
    pos_y: float
    locked: bool
    system_id: int
    system_name: str
    constellation_id: int | None
    constellation_name: str | None
    region_id: int | None
    region_name: str | None
    security_status: float | None
    security_class: str | None
    wh_effect_name: str | None
    class_name: str | None
    wh_effect_buffs: dict[str, int | float] | None
    wh_effect_debuffs: dict[str, int | float] | None
    statics: list[StaticInfo] | None

    @classmethod
    def from_source(cls, source: EnrichedNodeSourceData) -> EnrichedNodeInfo:
        """Create an EnrichedNodeInfo from source data."""
        statics = None
        if source.static_codes:
            target_classes = source.static_target_classes or []
            statics = [
                StaticInfo(
                    code=code,
                    target_class_name=SYSTEM_CLASS_MAPPING.get(target_classes[i]) if i < len(target_classes) else None,
                )
                for i, code in enumerate(source.static_codes)
            ]

        return cls(
            id=source.id,
            pos_x=source.pos_x,
            pos_y=source.pos_y,
            locked=source.locked,
            system_id=source.system_id,
            system_name=source.system_name,
            constellation_id=source.constellation_id,
            constellation_name=source.constellation_name,
            region_id=source.region_id,
            region_name=source.region_name,
            security_status=source.security_status,
            security_class=source.security_class,
            wh_effect_name=source.wh_effect_name,
            class_name=SYSTEM_CLASS_MAPPING.get(source.system_class) if source.system_class is not None else None,
            wh_effect_buffs=apply_class_multiplier(source.raw_buffs, source.system_class),
            wh_effect_debuffs=apply_class_multiplier(source.raw_debuffs, source.system_class),
            statics=statics,
        )


class EnrichedLinkInfo(msgspec.Struct):
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
    mass_usage: int
    date_mass_updated: datetime


class CharacterContext(msgspec.Struct):
    """Character context for access checks."""

    user_id: UUID
    corporation_id: int | None
    alliance_id: int | None
    character_ids: list[int] = []


class EnrichedSignatureInfo(msgspec.Struct):
    """Enriched signature information for API responses."""

    id: UUID
    node_id: UUID
    code: str
    group_type: str
    subgroup: str | None
    type: str | None
    link_id: UUID | None
    wormhole_id: int | None
    wormhole_code: str | None  # Enriched from wormhole table


class NodeConnectionInfo(msgspec.Struct):
    """Connection (link) information for a node, with system names."""

    id: UUID
    source_node_id: UUID
    target_node_id: UUID
    wormhole_code: str | None
    source_system_name: str
    target_system_name: str


class NodeConnectionsResponse(msgspec.Struct):
    """Response containing all connections for a node."""

    node_id: UUID
    connections: list[NodeConnectionInfo]


class MapDetailResponse(msgspec.Struct):
    """Full map with nodes and links."""

    map: MapInfo
    nodes: list[EnrichedNodeInfo]
    links: list[EnrichedLinkInfo]
    last_event_id: str | None = None  # For SSE Last-Event-ID on reconnect


class NodeSignaturesResponse(msgspec.Struct):
    """Signatures for a specific node."""

    node_id: UUID
    signatures: list[EnrichedSignatureInfo]


class MapListResponse(msgspec.Struct):
    """List of maps."""

    maps: list[MapInfo]


class PublicMapInfo(msgspec.Struct):
    """Public map information with subscription data."""

    id: UUID
    owner_id: UUID
    name: str
    description: str | None
    date_created: datetime
    date_updated: datetime
    is_public: bool = True
    public_read_only: bool = True
    edge_type: EdgeType = EdgeType.DEFAULT
    rankdir: RankDir = RankDir.TB
    auto_layout: bool = False
    node_sep: int = 60
    rank_sep: int = 60
    edit_access: bool = False
    subscription_count: int = 0
    is_subscribed: bool = False


class PublicMapListResponse(msgspec.Struct):
    """List of public maps with pagination info."""

    maps: list[PublicMapInfo]
    total: int
    limit: int
    offset: int


class SubscriptionResponse(msgspec.Struct):
    """Response after subscribing/unsubscribing."""

    map_id: UUID
    subscribed: bool
    subscription_count: int


class UserCharacter(msgspec.Struct):
    """User character info for context lookups."""

    corporation_id: int | None
    alliance_id: int | None


class UserCharacterId(msgspec.Struct):
    """User character ID for access checks."""

    id: int


# Delete response structs for 202 Accepted responses


class DeleteNodeResponse(msgspec.Struct):
    """Response for node deletion, includes cascaded link deletions."""

    node_id: UUID
    deleted_link_ids: list[UUID]
    deleted_signature_ids: list[UUID]


class DeleteLinkResponse(msgspec.Struct):
    """Response for link deletion."""

    link_id: UUID


class DeleteMapResponse(msgspec.Struct):
    """Response for map deletion, includes all deleted nodes and links."""

    map_id: UUID
    deleted_node_ids: list[UUID]
    deleted_link_ids: list[UUID]


# Minimal response structs for mutation endpoints - full data delivered via SSE


class CreateNodeResponse(msgspec.Struct):
    """Minimal response for node creation - full data via SSE."""

    node_id: UUID


class CreateLinkResponse(msgspec.Struct):
    """Minimal response for link creation - full data via SSE."""

    link_id: UUID


class UpdateNodeResponse(msgspec.Struct):
    """Minimal response for node update - full data via SSE."""

    node_id: UUID


class UpdateLinkResponse(msgspec.Struct):
    """Minimal response for link update - full data via SSE."""

    link_id: UUID


def _validate_node_rank_sep(value: int | None, field_name: str) -> None:
    """Validate node_sep or rank_sep value."""
    if value is not None and (value < 20 or value > 500 or value % 20 != 0):
        msg = f"{field_name} must be a multiple of 20 between 20 and 500"
        raise ValueError(msg)


@dataclass
class CreateMapRequest:
    """Request body for creating a map."""

    name: str
    description: str | None = None
    is_public: bool = False
    public_read_only: bool = True
    edge_type: EdgeType = EdgeType.DEFAULT
    rankdir: RankDir = RankDir.TB
    auto_layout: bool = False
    node_sep: int = 60
    rank_sep: int = 60

    def __post_init__(self) -> None:
        _validate_node_rank_sep(self.node_sep, "node_sep")
        _validate_node_rank_sep(self.rank_sep, "rank_sep")


@dataclass
class UpdateMapRequest:
    """Request body for updating a map."""

    name: str | None = None
    description: str | None = None
    is_public: bool | None = None
    public_read_only: bool | None = None
    edge_type: EdgeType | None = None
    rankdir: RankDir | None = None
    auto_layout: bool | None = None
    node_sep: int | None = None
    rank_sep: int | None = None

    def __post_init__(self) -> None:
        _validate_node_rank_sep(self.node_sep, "node_sep")
        _validate_node_rank_sep(self.rank_sep, "rank_sep")


@dataclass
class AddCharacterAccessRequest:
    """Request body for adding character access."""

    character_id: int
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


@dataclass
class UpdateNodePositionRequest:
    """Request body for updating a node's position."""

    pos_x: float
    pos_y: float


@dataclass
class UpdateNodeSystemRequest:
    """Request body for updating a node's system."""

    system_id: int


@dataclass
class UpdateNodeLockedRequest:
    """Request body for updating a node's locked status."""

    locked: bool


@dataclass
class UpdateLinkRequest:
    """Request body for updating a link."""

    wormhole_id: int | None = None
    lifetime_status: str | None = None
    mass_usage: int | None = None
    reverse: bool | None = None


# Signature DTOs


class CreateSignatureResponse(msgspec.Struct):
    """Minimal response for signature creation - full data via SSE."""

    signature_id: UUID


class UpdateSignatureResponse(msgspec.Struct):
    """Minimal response for signature update - full data via SSE."""

    signature_id: UUID


class DeleteSignatureResponse(msgspec.Struct):
    """Response for signature deletion."""

    signature_id: UUID


class BulkSignatureResponse(msgspec.Struct):
    """Response for bulk signature operations."""

    created: list[UUID]
    updated: list[UUID]
    deleted: list[UUID]


@dataclass
class CreateSignatureRequest:
    """Request body for creating a signature."""

    node_id: UUID
    code: str
    group_type: str  # "signature" or "anomaly"
    subgroup: str | None = None
    type: str | None = None
    link_id: UUID | None = None
    wormhole_id: int | None = None


class UpdateSignatureRequest(msgspec.Struct):
    """Request body for updating a signature.

    Used with partial=True DTO config - only provided fields will be in the payload.
    """

    code: str | None = None
    group_type: str | None = None
    subgroup: str | None = None
    type: str | None = None
    link_id: UUID | None = None
    wormhole_id: int | None = None


class UpdateSignatureDTO(MsgspecDTO[UpdateSignatureRequest]):
    """Partial DTO for signature updates - only provided fields are included."""

    config = DTOConfig(partial=True)


@dataclass
class BulkSignatureItem:
    """A single signature in a bulk request."""

    code: str
    group_type: str  # "signature" or "anomaly"
    subgroup: str | None = None
    type: str | None = None
    link_id: UUID | None = None
    wormhole_id: int | None = None


@dataclass
class BulkCreateSignatureRequest:
    """Request body for bulk creating/updating signatures."""

    signatures: list[BulkSignatureItem]


@dataclass
class SetLinkTypeRequest:
    """Request body for setting wormhole type on a link from a specific node."""

    wormhole_id: int
    from_node_id: UUID  # The node the user is setting the type from


@dataclass
class CreateConnectionFromSignatureRequest:
    """Request body for creating a new node + connection from a signature."""

    system_id: int  # Destination system
    pos_x: float
    pos_y: float
    wormhole_id: int | None = None  # Optional, defaults to K162


class CreateConnectionFromSignatureResponse(msgspec.Struct):
    """Response for creating a connection from a signature."""

    node_id: UUID  # The newly created node
    link_id: UUID  # The newly created link
    signature_id: UUID  # The updated signature
