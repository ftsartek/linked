from __future__ import annotations

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

    config = DTOConfig(exclude={"systems.0.system_class"})


class WormholeSearchResult(msgspec.Struct):
    """A single wormhole search result."""

    id: int
    code: str


class WormholeSearchResponse(msgspec.Struct):
    """Response containing wormhole search results."""

    wormholes: list[WormholeSearchResult]


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
