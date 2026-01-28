"""Character location tracking service with Valkey caching."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol, TypeVar, cast
from uuid import UUID

import msgspec

from routes.users.location.queries import (
    DELETE_REFRESH_TOKEN,
    GET_CHARACTER_FOR_LOCATION,
    GET_SHIP_TYPE_NAME,
    GET_STATION_NAME,
    GET_SYSTEM_NAME,
    UPDATE_REFRESH_TOKEN,
)

if TYPE_CHECKING:
    from sqlspec import AsyncDriverAdapterBase

    from esi_client import ESIClient
    from services.encryption import EncryptionService
    from services.eve_sso import EveSSOService
    from utils.valkey import NamespacedValkey

from esi_client.exceptions import ESIError, ESIForbiddenError

logger = logging.getLogger(__name__)


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
    error: str  # "no_scope" | "token_expired" | "token_revoked" | "esi_error"


@dataclass
class CharacterWithToken:
    """Character with refresh token info for location queries."""

    id: int
    name: str
    token: bytes | None
    has_location_scope: bool


@dataclass
class _CachedLocationState:
    """Internal state for cached location data during refresh."""

    online: CachedOnline | None
    online_stale: bool
    location: CachedLocation | None
    location_stale: bool
    ship: CachedShip | None
    ship_stale: bool
    is_offline: bool

    @property
    def any_stale(self) -> bool:
        """Check if any data is stale."""
        return self.online_stale or self.location_stale or self.ship_stale


@dataclass
class _ResolvedNames:
    """Resolved entity names for location data."""

    system_name: str | None
    station_name: str | None
    structure_name: str | None
    ship_type_name: str | None


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

    # -------------------------------------------------------------------------
    # Cache key helpers
    # -------------------------------------------------------------------------

    def _cache_key(self, character_id: int, data_type: str) -> str:
        """Generate cache key for character location data."""
        return f"{character_id}:{data_type}"

    # -------------------------------------------------------------------------
    # Name resolution helpers (database lookups)
    # -------------------------------------------------------------------------

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
            # Structure access forbidden - could be token revoked or no ACL access
            # For structures, 403 usually means no ACL access, not token revocation
            await self.cache.setex(cache_key, STRUCTURE_UNKNOWN_TTL, UNKNOWN_STRUCTURE_NAME.encode())
            return UNKNOWN_STRUCTURE_NAME
        except ESIError:
            return UNKNOWN_STRUCTURE_NAME

    # -------------------------------------------------------------------------
    # Generic cache operations
    # -------------------------------------------------------------------------

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

    # -------------------------------------------------------------------------
    # Token management
    # -------------------------------------------------------------------------

    async def _persist_rotated_token(self, character_id: int, new_refresh_token: str) -> None:
        """Persist a rotated refresh token to the database.

        EVE SSO rotates refresh tokens on each use - the new token must be
        persisted to maintain valid authentication.

        Args:
            character_id: Character ID the token belongs to
            new_refresh_token: The new refresh token from SSO response
        """
        encrypted_token = self.encryption_service.encrypt(new_refresh_token)
        await self.db_session.execute(
            UPDATE_REFRESH_TOKEN,
            character_id,
            encrypted_token,
        )

    async def _invalidate_token(self, character_id: int) -> None:
        """Delete a character's refresh token when it has been revoked.

        Called when ESI returns 403 Forbidden for location/online/ship endpoints,
        indicating the user has revoked the application's access.

        Args:
            character_id: Character ID whose token should be deleted
        """
        logger.info("Invalidating revoked token for character %d", character_id)
        await self.db_session.execute(DELETE_REFRESH_TOKEN, character_id)

    async def _get_access_token(self, encrypted_token: bytes, character_id: int) -> str | None:
        """Decrypt refresh token and get fresh access token.

        Also persists the rotated refresh token returned by EVE SSO.

        Args:
            encrypted_token: Encrypted refresh token from database
            character_id: Character ID for token persistence

        Returns:
            Fresh access token or None if refresh failed
        """
        try:
            refresh_token = self.encryption_service.decrypt(encrypted_token)
            token_response = await self.sso_service.refresh_access_token(refresh_token)

            # EVE SSO rotates refresh tokens - persist the new one
            await self._persist_rotated_token(character_id, token_response.refresh_token)

            return token_response.access_token
        except Exception:
            return None

    # -------------------------------------------------------------------------
    # ESI data fetching (individual endpoints)
    # -------------------------------------------------------------------------

    async def _fetch_online(
        self, client: ESIClient, char_id: int, access_token: str
    ) -> tuple[CachedOnline | None, bool]:
        """Fetch online status from ESI and cache it.

        Returns:
            Tuple of (cached data or None, token_revoked flag)
        """
        try:
            esi_data = await client.get_character_online(access_token, char_id)
            cached = CachedOnline(online=esi_data.online, fetched_at=time.time())
            await self._set_cached(char_id, "online", cached, ONLINE_TTL)
            return cached, False
        except ESIForbiddenError:
            # Token has been revoked by the user
            await self._invalidate_token(char_id)
            return None, True
        except ESIError:
            return None, False

    async def _fetch_location(
        self, client: ESIClient, char_id: int, access_token: str
    ) -> tuple[CachedLocation | None, bool]:
        """Fetch location from ESI and cache it.

        Returns:
            Tuple of (cached data or None, token_revoked flag)
        """
        try:
            esi_data = await client.get_character_location(access_token, char_id)
            cached = CachedLocation(
                solar_system_id=esi_data.solar_system_id,
                station_id=esi_data.station_id,
                structure_id=esi_data.structure_id,
                fetched_at=time.time(),
            )
            await self._set_cached(char_id, "position", cached, LOCATION_TTL)
            return cached, False
        except ESIForbiddenError:
            # Token has been revoked by the user
            await self._invalidate_token(char_id)
            return None, True
        except ESIError:
            return None, False

    async def _fetch_ship(self, client: ESIClient, char_id: int, access_token: str) -> tuple[CachedShip | None, bool]:
        """Fetch ship from ESI and cache it.

        Returns:
            Tuple of (cached data or None, token_revoked flag)
        """
        try:
            esi_data = await client.get_character_ship(access_token, char_id)
            cached = CachedShip(
                ship_type_id=esi_data.ship_type_id,
                ship_name=esi_data.ship_name,
                fetched_at=time.time(),
            )
            await self._set_cached(char_id, "ship", cached, SHIP_TTL)
            return cached, False
        except ESIForbiddenError:
            # Token has been revoked by the user
            await self._invalidate_token(char_id)
            return None, True
        except ESIError:
            return None, False

    async def _fetch_stale_data(
        self,
        char_id: int,
        access_token: str,
        online_stale: bool,
        loc_stale: bool,
        ship_stale: bool,
    ) -> tuple[CachedOnline | None, CachedLocation | None, CachedShip | None, bool]:
        """Fetch all stale data concurrently using a single ESI client connection.

        Returns:
            Tuple of (online, location, ship, token_revoked)
        """
        if not (online_stale or loc_stale or ship_stale):
            return None, None, None, False

        online_result: CachedOnline | None = None
        location_result: CachedLocation | None = None
        ship_result: CachedShip | None = None
        token_revoked = False

        async with self.esi_client as client:
            tasks: list[tuple[str, asyncio.Task[tuple[CachedOnline | CachedLocation | CachedShip | None, bool]]]] = []
            if online_stale:
                tasks.append(("online", asyncio.create_task(self._fetch_online(client, char_id, access_token))))
            if loc_stale:
                tasks.append(("location", asyncio.create_task(self._fetch_location(client, char_id, access_token))))
            if ship_stale:
                tasks.append(("ship", asyncio.create_task(self._fetch_ship(client, char_id, access_token))))

            for name, task in tasks:
                result, revoked = await task
                if revoked:
                    token_revoked = True
                if name == "online":
                    online_result = cast(CachedOnline | None, result)
                elif name == "location":
                    location_result = cast(CachedLocation | None, result)
                elif name == "ship":
                    ship_result = cast(CachedShip | None, result)

        return online_result, location_result, ship_result, token_revoked

    # -------------------------------------------------------------------------
    # Location refresh orchestration helpers
    # -------------------------------------------------------------------------

    async def _get_cached_location_state(self, char_id: int) -> _CachedLocationState:
        """Get all cached location data with staleness info.

        Args:
            char_id: Character ID to get cached data for

        Returns:
            Cached state with online, location, ship data and staleness flags
        """
        online, online_stale = await self._get_cached(char_id, "online", CachedOnline, ONLINE_STALE_THRESHOLD)

        # Use longer stale threshold if character is known to be offline
        is_offline = online is not None and not online.online
        loc_threshold = OFFLINE_STALE_THRESHOLD if is_offline else LOCATION_STALE_THRESHOLD
        ship_threshold = OFFLINE_STALE_THRESHOLD if is_offline else SHIP_STALE_THRESHOLD

        location, location_stale = await self._get_cached(char_id, "position", CachedLocation, loc_threshold)
        ship, ship_stale = await self._get_cached(char_id, "ship", CachedShip, ship_threshold)

        return _CachedLocationState(
            online=online,
            online_stale=online_stale,
            location=location,
            location_stale=location_stale,
            ship=ship,
            ship_stale=ship_stale,
            is_offline=is_offline,
        )

    async def _resolve_location_names(
        self,
        location: CachedLocation,
        ship: CachedShip | None,
        access_token: str | None,
    ) -> _ResolvedNames:
        """Resolve all entity names for location data.

        Args:
            location: Cached location data
            ship: Cached ship data (optional)
            access_token: Access token for ESI calls (needed for structure names)

        Returns:
            Resolved names for system, station, structure, and ship type
        """
        system_name = await self._get_system_name(location.solar_system_id)
        ship_type_name = await self._get_ship_type_name(ship.ship_type_id) if ship else None
        station_name = await self._get_station_name(location.station_id) if location.station_id else None

        # Structure name requires access token for ESI lookup
        structure_name: str | None = None
        if location.structure_id and access_token:
            structure_name = await self._get_structure_name(location.structure_id, access_token)

        return _ResolvedNames(
            system_name=system_name,
            station_name=station_name,
            structure_name=structure_name,
            ship_type_name=ship_type_name,
        )

    def _build_location_response(
        self,
        char: CharacterWithToken,
        state: _CachedLocationState,
        names: _ResolvedNames,
    ) -> CharacterLocationData:
        """Build the final location response from cached state and resolved names.

        Args:
            char: Character info
            state: Cached location state (must have valid location)
            names: Resolved entity names

        Returns:
            Complete CharacterLocationData response
        """
        location = state.location
        assert location is not None  # Caller must ensure location is valid

        # Determine overall staleness and last update time
        timestamps = [location.fetched_at]
        if state.online:
            timestamps.append(state.online.fetched_at)
        if state.ship:
            timestamps.append(state.ship.fetched_at)

        oldest_fetch = min(timestamps)
        stale_threshold = OFFLINE_STALE_THRESHOLD if state.is_offline else LOCATION_STALE_THRESHOLD
        is_stale = (time.time() - oldest_fetch) > stale_threshold

        return CharacterLocationData(
            character_id=char.id,
            character_name=char.name,
            solar_system_id=location.solar_system_id,
            solar_system_name=names.system_name,
            station_id=location.station_id,
            station_name=names.station_name,
            structure_id=location.structure_id,
            structure_name=names.structure_name,
            online=state.online.online if state.online else None,
            ship_type_id=state.ship.ship_type_id if state.ship else None,
            ship_type_name=names.ship_type_name,
            ship_name=state.ship.ship_name if state.ship else None,
            last_updated=datetime.fromtimestamp(oldest_fetch, tz=UTC),
            is_stale=is_stale,
        )

    # -------------------------------------------------------------------------
    # Main refresh logic
    # -------------------------------------------------------------------------

    async def _refresh_character_location(
        self,
        char: CharacterWithToken,
    ) -> CharacterLocationData | CharacterLocationError:
        """Refresh location data for a single character.

        Orchestrates the full refresh flow:
        1. Get cached data and determine staleness
        2. Acquire access token if needed
        3. Fetch stale data from ESI
        4. Resolve entity names
        5. Build and return response
        """
        # Step 1: Get cached data with staleness info
        state = await self._get_cached_location_state(char.id)

        # Step 2: Get access token if we need to refresh stale data
        access_token: str | None = None
        if char.token is not None:
            access_token = await self._get_access_token(char.token, char.id)

        # Step 3: Fetch stale data if we have an access token
        if state.any_stale:
            if access_token is None:
                error = "no_scope" if char.token is None else "token_expired"
                return CharacterLocationError(character_id=char.id, character_name=char.name, error=error)

            new_online, new_location, new_ship, token_revoked = await self._fetch_stale_data(
                char.id, access_token, state.online_stale, state.location_stale, state.ship_stale
            )

            if token_revoked:
                return CharacterLocationError(character_id=char.id, character_name=char.name, error="token_revoked")

            # Update state with fresh data
            state.online = new_online or state.online
            state.location = new_location or state.location
            state.ship = new_ship or state.ship

        # Validate we have location data
        if state.location is None:
            return CharacterLocationError(character_id=char.id, character_name=char.name, error="esi_error")

        # Step 4: Resolve entity names
        names = await self._resolve_location_names(state.location, state.ship, access_token)

        # Step 5: Build and return response
        return self._build_location_response(char, state, names)

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
