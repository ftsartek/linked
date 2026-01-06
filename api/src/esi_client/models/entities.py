"""ESI models for character, corporation, and alliance entities."""

from __future__ import annotations

import msgspec


class ESICharacter(msgspec.Struct):
    """ESI character public information."""

    name: str
    corporation_id: int
    alliance_id: int | None = None
    birthday: str | None = None
    bloodline_id: int | None = None
    description: str | None = None
    faction_id: int | None = None
    gender: str | None = None
    race_id: int | None = None
    security_status: float | None = None
    title: str | None = None


class ESICorporation(msgspec.Struct):
    """ESI corporation public information."""

    name: str
    ticker: str
    alliance_id: int | None = None
    ceo_id: int | None = None
    creator_id: int | None = None
    date_founded: str | None = None
    description: str | None = None
    faction_id: int | None = None
    home_station_id: int | None = None
    member_count: int | None = None
    shares: int | None = None
    tax_rate: float | None = None
    url: str | None = None
    war_eligible: bool | None = None


class ESIAlliance(msgspec.Struct):
    """ESI alliance public information."""

    name: str
    ticker: str
    creator_corporation_id: int | None = None
    creator_id: int | None = None
    date_founded: str | None = None
    executor_corporation_id: int | None = None
    faction_id: int | None = None
