"""Character location tracking service with Valkey caching."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol, TypeVar, cast
from uuid import UUID

import msgspec

from routes.users.location.queries import (
    GET_CHARACTER_FOR_LOCATION,
    GET_SHIP_TYPE_NAME,
    GET_STATION_NAME,
    GET_SYSTEM_NAME,
)

if TYPE_CHECKING:
    from sqlspec import AsyncDriverAdapterBase

    from esi_client import ESIClient
    from services.encryption import EncryptionService
    from services.eve_sso import EveSSOService
    from utils.valkey import NamespacedValkey

from esi_client.exceptions import ESIError, ESIForbiddenError


class CachedData(Protocol):
    """Protocol for cached data with timestamp."""

    fetched_at: float


T = TypeVar("T", bound=CachedData)

# Stale thresholds (seconds) - data is considered stale after this time
LOCATION_STALE_THRESHOLD = 10
ONLINE_STALE_THRESHOLD = 60
SHIP_STALE_THRESHOLD = 60

# When character is offline, use longer stale threshold (they're not moving)
OFFLINE_STALE_THRESHOLD = 120

# Hard TTL (seconds) - data expires from cache entirely after this time
LOCATION_TTL = 300  # 5 minutes
ONLINE_TTL = 600  # 10 minutes
SHIP_TTL = 600  # 10 minutes

# Structure name cache TTLs
STRUCTURE_NAME_TTL = 259200  # 3 days for known names
STRUCTURE_UNKNOWN_TTL = 3600  # 1 hour for forbidden/unknown
UNKNOWN_STRUCTURE_NAME = "Upwell Structure"


class CachedLocation(msgspec.Struct):
    """Cached location data with timestamp."""

    solar_system_id: int
    station_id: int | None
    structure_id: int | None
    fetched_at: float


class CachedOnline(msgspec.Struct):
    """Cached online status with timestamp."""

    online: bool
    fetched_at: float


class CachedShip(msgspec.Struct):
    """Cached ship data with timestamp."""

    ship_type_id: int
    ship_name: str
    fetched_at: float


@dataclass
class CharacterLocationData:
    """Combined location data for a character."""

    character_id: int
    character_name: str
    solar_system_id: int | None
    solar_system_name: str | None
    station_id: int | None
    station_name: str | None
    structure_id: int | None
    structure_name: str | None
    online: bool | None
    ship_type_id: int | None
    ship_type_name: str | None
    ship_name: str | None
    last_updated: datetime
    is_stale: bool


@dataclass
class CharacterLocationError:
    """Error fetching location for a character."""

    character_id: int
    character_name: str
    error: str  # "no_scope" | "token_expired" | "esi_error"


@dataclass
class CharacterWithToken:
    """Character with refresh token info for location queries."""

    id: int
    name: str
    token: bytes | None
    has_location_scope: bool


class LocationService:
    """Service for fetching and caching character locations."""

    def __init__(
        self,
        db_session: AsyncDriverAdapterBase,
        encryption_service: EncryptionService,
        sso_service: EveSSOService,
        esi_client: ESIClient,
        cache: NamespacedValkey,
    ) -> None:
        self.db_session = db_session
        self.encryption_service = encryption_service
        self.sso_service = sso_service
        self.esi_client = esi_client
        self.cache = cache

    def _cache_key(self, character_id: int, data_type: str) -> str:
        """Generate cache key for character location data."""
        return f"{character_id}:{data_type}"

    async def _get_system_name(self, system_id: int) -> str | None:
        """Get solar system name by ID."""
        return await self.db_session.select_value(GET_SYSTEM_NAME, system_id)

    async def _get_ship_type_name(self, type_id: int) -> str | None:
        """Get ship type name by ID."""
        return await self.db_session.select_value(GET_SHIP_TYPE_NAME, type_id)

    async def _get_station_name(self, station_id: int) -> str | None:
        """Get NPC station name by ID from database."""
        return await self.db_session.select_value(GET_STATION_NAME, station_id)

    async def _get_structure_name(self, structure_id: int, access_token: str) -> str:
        """Get structure name, using cache or fetching from ESI.

        Uses long cache (3 days) for known names, short cache (1 hour) for forbidden.
        """
        cache_key = f"structure:{structure_id}"
        cached = cast(bytes | None, await self.cache.get(cache_key))

        if cached is not None:
            return cached.decode()

        try:
            async with self.esi_client as client:
                structure = await client.get_structure(access_token, structure_id)
                name = structure.name
                await self.cache.setex(cache_key, STRUCTURE_NAME_TTL, name.encode())
                return name
        except ESIForbiddenError:
            await self.cache.setex(cache_key, STRUCTURE_UNKNOWN_TTL, UNKNOWN_STRUCTURE_NAME.encode())
            return UNKNOWN_STRUCTURE_NAME
        except ESIError:
            return UNKNOWN_STRUCTURE_NAME

    async def _get_cached(
        self,
        character_id: int,
        data_type: str,
        schema_type: type[T],
        stale_threshold: float,
    ) -> tuple[T | None, bool]:
        """Get cached data and staleness status.

        Returns:
            Tuple of (data or None, is_stale)
        """
        key = self._cache_key(character_id, data_type)
        raw = cast(bytes | None, await self.cache.get(key))

        if raw is None:
            return None, True

        try:
            data = msgspec.json.decode(raw, type=schema_type)
            is_stale = (time.time() - data.fetched_at) > stale_threshold
            return data, is_stale
        except msgspec.DecodeError:
            return None, True

    async def _set_cached(
        self,
        character_id: int,
        data_type: str,
        data: msgspec.Struct,
        ttl: int,
    ) -> None:
        """Store data in cache with TTL."""
        key = self._cache_key(character_id, data_type)
        raw = msgspec.json.encode(data)
        await self.cache.setex(key, ttl, raw)

    async def _get_access_token(self, encrypted_token: bytes) -> str | None:
        """Decrypt refresh token and get fresh access token."""
        try:
            refresh_token = self.encryption_service.decrypt(encrypted_token)
            token_response = await self.sso_service.refresh_access_token(refresh_token)
            return token_response.access_token
        except Exception:
            return None

    async def _fetch_online(self, client: ESIClient, char_id: int, access_token: str) -> CachedOnline | None:
        """Fetch online status from ESI and cache it."""
        try:
            esi_data = await client.get_character_online(access_token, char_id)
            cached = CachedOnline(online=esi_data.online, fetched_at=time.time())
            await self._set_cached(char_id, "online", cached, ONLINE_TTL)
            return cached
        except ESIError:
            return None

    async def _fetch_location(self, client: ESIClient, char_id: int, access_token: str) -> CachedLocation | None:
        """Fetch location from ESI and cache it."""
        try:
            esi_data = await client.get_character_location(access_token, char_id)
            cached = CachedLocation(
                solar_system_id=esi_data.solar_system_id,
                station_id=esi_data.station_id,
                structure_id=esi_data.structure_id,
                fetched_at=time.time(),
            )
            await self._set_cached(char_id, "position", cached, LOCATION_TTL)
            return cached
        except ESIError:
            return None

    async def _fetch_ship(self, client: ESIClient, char_id: int, access_token: str) -> CachedShip | None:
        """Fetch ship from ESI and cache it."""
        try:
            esi_data = await client.get_character_ship(access_token, char_id)
            cached = CachedShip(
                ship_type_id=esi_data.ship_type_id,
                ship_name=esi_data.ship_name,
                fetched_at=time.time(),
            )
            await self._set_cached(char_id, "ship", cached, SHIP_TTL)
            return cached
        except ESIError:
            return None

    async def _fetch_stale_data(
        self,
        char_id: int,
        access_token: str,
        online_stale: bool,
        loc_stale: bool,
        ship_stale: bool,
    ) -> tuple[CachedOnline | None, CachedLocation | None, CachedShip | None]:
        """Fetch all stale data concurrently using a single ESI client connection."""
        if not (online_stale or loc_stale or ship_stale):
            return None, None, None

        online_result: CachedOnline | None = None
        location_result: CachedLocation | None = None
        ship_result: CachedShip | None = None

        async with self.esi_client as client:
            tasks: list[tuple[str, asyncio.Task[CachedOnline | CachedLocation | CachedShip | None]]] = []
            if online_stale:
                tasks.append(("online", asyncio.create_task(self._fetch_online(client, char_id, access_token))))
            if loc_stale:
                tasks.append(("location", asyncio.create_task(self._fetch_location(client, char_id, access_token))))
            if ship_stale:
                tasks.append(("ship", asyncio.create_task(self._fetch_ship(client, char_id, access_token))))

            for name, task in tasks:
                result = await task
                if name == "online":
                    online_result = cast(CachedOnline | None, result)
                elif name == "location":
                    location_result = cast(CachedLocation | None, result)
                elif name == "ship":
                    ship_result = cast(CachedShip | None, result)

        return online_result, location_result, ship_result

    async def _refresh_character_location(
        self,
        char: CharacterWithToken,
    ) -> CharacterLocationData | CharacterLocationError:
        """Refresh location data for a single character."""
        # Check all caches first
        online, online_stale = await self._get_cached(char.id, "online", CachedOnline, ONLINE_STALE_THRESHOLD)

        # Use longer stale threshold if character is known to be offline
        is_offline = online is not None and not online.online
        loc_threshold = OFFLINE_STALE_THRESHOLD if is_offline else LOCATION_STALE_THRESHOLD
        ship_threshold = OFFLINE_STALE_THRESHOLD if is_offline else SHIP_STALE_THRESHOLD

        location, loc_stale = await self._get_cached(char.id, "position", CachedLocation, loc_threshold)
        ship, ship_stale = await self._get_cached(char.id, "ship", CachedShip, ship_threshold)

        # Get access token - needed for stale data refresh and structure name lookup
        access_token: str | None = None
        if char.token is not None:
            access_token = await self._get_access_token(char.token)

        # Fetch stale data if we have an access token
        if online_stale or loc_stale or ship_stale:
            if access_token is None:
                if char.token is None:
                    return CharacterLocationError(character_id=char.id, character_name=char.name, error="no_scope")
                return CharacterLocationError(character_id=char.id, character_name=char.name, error="token_expired")

            new_online, new_location, new_ship = await self._fetch_stale_data(
                char.id, access_token, online_stale, loc_stale, ship_stale
            )
            online = new_online or online
            location = new_location or location
            ship = new_ship or ship

        if location is None:
            return CharacterLocationError(character_id=char.id, character_name=char.name, error="esi_error")

        # Determine overall staleness and last update time
        timestamps = [location.fetched_at]
        if online:
            timestamps.append(online.fetched_at)
        if ship:
            timestamps.append(ship.fetched_at)

        oldest_fetch = min(timestamps)
        is_stale = (time.time() - oldest_fetch) > (OFFLINE_STALE_THRESHOLD if is_offline else LOCATION_STALE_THRESHOLD)

        # Resolve names from database/ESI
        system_name = await self._get_system_name(location.solar_system_id)
        ship_type_name = await self._get_ship_type_name(ship.ship_type_id) if ship else None
        station_name = await self._get_station_name(location.station_id) if location.station_id else None

        # Resolve structure name (requires access token for ESI lookup)
        structure_name: str | None = None
        if location.structure_id and access_token:
            structure_name = await self._get_structure_name(location.structure_id, access_token)

        return CharacterLocationData(
            character_id=char.id,
            character_name=char.name,
            solar_system_id=location.solar_system_id,
            solar_system_name=system_name,
            station_id=location.station_id,
            station_name=station_name,
            structure_id=location.structure_id,
            structure_name=structure_name,
            online=online.online if online else None,
            ship_type_id=ship.ship_type_id if ship else None,
            ship_type_name=ship_type_name,
            ship_name=ship.ship_name if ship else None,
            last_updated=datetime.fromtimestamp(oldest_fetch, tz=UTC),
            is_stale=is_stale,
        )

    async def refresh_character_location(
        self,
        character_id: int,
        user_id: UUID,
    ) -> CharacterLocationData | CharacterLocationError | None:
        """Refresh location data for a single character owned by the user.

        Returns:
            CharacterLocationData on success,
            CharacterLocationError on scope/token issues,
            None if character not found or not owned by user.
        """
        char = await self.db_session.select_one_or_none(
            GET_CHARACTER_FOR_LOCATION,
            character_id,
            user_id,
            schema_type=CharacterWithToken,
        )

        if char is None:
            return None

        if not char.has_location_scope or char.token is None:
            return CharacterLocationError(character_id=char.id, character_name=char.name, error="no_scope")

        return await self._refresh_character_location(char)
