"""ESI models for character location, online status, and ship."""

from __future__ import annotations

import msgspec


class ESICharacterLocation(msgspec.Struct):
    """ESI character location response.

    GET /characters/{character_id}/location/
    Requires: esi-location.read_location.v1 scope
    """

    solar_system_id: int
    station_id: int | None = None
    structure_id: int | None = None


class ESICharacterOnline(msgspec.Struct):
    """ESI character online status response.

    GET /characters/{character_id}/online/
    Requires: esi-location.read_online.v1 scope
    """

    online: bool
    last_login: str | None = None
    last_logout: str | None = None
    logins: int | None = None


class ESICharacterShip(msgspec.Struct):
    """ESI character current ship response.

    GET /characters/{character_id}/ship/
    Requires: esi-location.read_ship_type.v1 scope
    """

    ship_item_id: int
    ship_name: str
    ship_type_id: int
