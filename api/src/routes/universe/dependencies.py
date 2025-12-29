from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SystemSearchResult:
    """A single system search result."""

    id: int
    name: str
    wh_class: int | None


@dataclass
class SystemSearchResponse:
    """Response containing system search results."""

    systems: list[SystemSearchResult]


@dataclass
class WormholeSearchResult:
    """A single wormhole search result."""

    id: int
    code: str


@dataclass
class WormholeSearchResponse:
    """Response containing wormhole search results."""

    wormholes: list[WormholeSearchResult]
