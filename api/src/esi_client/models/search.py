from __future__ import annotations

from msgspec import Struct


class ESISearchResponse(Struct):
    """Response from ESI character search endpoint."""

    agent: list[int] | None = None
    alliance: list[int] | None = None
    character: list[int] | None = None
    constellation: list[int] | None = None
    corporation: list[int] | None = None
    faction: list[int] | None = None
    inventory_type: list[int] | None = None
    region: list[int] | None = None
    solar_system: list[int] | None = None
    station: list[int] | None = None
    structure: list[int] | None = None


class ESINameResult(Struct):
    """Single result from ESI universe/names endpoint."""

    id: int
    name: str
    category: str
