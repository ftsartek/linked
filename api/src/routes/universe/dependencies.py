from __future__ import annotations

from uuid import UUID

import msgspec
from litestar.dto.config import DTOConfig
from litestar.dto.msgspec_dto import MsgspecDTO

from utils.class_mapping import SYSTEM_CLASS_MAPPING


class SystemSearchResult(msgspec.Struct):
    """A single system search result."""

    id: int
    name: str
    system_class: int | None

    @property
    def class_name(self) -> str | None:
        """Name of the system class."""
        if self.system_class is None:
            return None
        return SYSTEM_CLASS_MAPPING.get(self.system_class)


class SystemSearchResponse(msgspec.Struct):
    """Response containing system search results."""

    systems: list[SystemSearchResult]


class SystemSearchResponseDTO(MsgspecDTO[SystemSearchResponse]):
    """DTO for a single system search result."""

    config = DTOConfig()


class ClassMapping(msgspec.Struct):
    """Mapping of wormhole classes to their names."""

    id: int

    @property
    def class_name(self) -> str:
        class_name = SYSTEM_CLASS_MAPPING.get(self.id)
        if class_name is None:
            return "?"
        return class_name


class WormholeSearchResult(msgspec.Struct):
    """A single wormhole search result."""

    id: int
    code: str
    target: ClassMapping
    sources: list[ClassMapping]


class WormholeSearchResponseDTO(MsgspecDTO[WormholeSearchResult]):
    """DTO for a single wormhole search result."""

    config = DTOConfig()


class EntitySearchResult(msgspec.Struct):
    """A single entity search result (character, corporation, or alliance)."""

    id: int
    name: str


class UniverseSearchResponse(msgspec.Struct):
    """Response containing universe entity search results."""

    characters: list[EntitySearchResult]
    corporations: list[EntitySearchResult]
    alliances: list[EntitySearchResult]


class LocalEntitySearchResult(msgspec.Struct):
    """A single local entity search result with type information."""

    id: int
    name: str
    entity_type: str  # "character" | "corporation" | "alliance"
    ticker: str | None = None


class LocalSearchResponse(msgspec.Struct):
    """Response containing local entity search results."""

    results: list[LocalEntitySearchResult]


class UserSearchResult(msgspec.Struct):
    """A single user search result (for admin management)."""

    user_id: UUID
    character_id: int
    character_name: str


class UserSearchResponse(msgspec.Struct):
    """Response containing user search results."""

    results: list[UserSearchResult]


class NeighbourSystem(msgspec.Struct):
    """A neighbouring system connected via stargate."""

    id: int
    name: str
    security_status: float | None
    system_class: int | None


class SystemDetails(msgspec.Struct):
    """Detailed information about a solar system."""

    id: int
    name: str
    radius: float | None
    planet_count: int
    moon_count: int
    station_count: int
    neighbours: list[NeighbourSystem]


class SystemDetailsDTO(MsgspecDTO[SystemDetails]):
    """DTO for system details response."""

    config = DTOConfig()
