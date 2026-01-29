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

from routes.maps.dependencies import NodeCharacterLocation
from routes.maps.queries import (
    GET_NODES_FOR_SYSTEM_IN_MAPS,
    GET_USER_MAPS_WITH_LOCATION_TRACKING,
)
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
    from routes.maps.publisher import EventPublisher
    from services.encryption import EncryptionService
    from services.eve_sso import EveSSOService
    from utils.valkey import NamespacedValkey

from esi_client.exceptions import ESIError, ESIForbiddenError

logger = logging.getLogger(__name__)


class ReferenceDataError(Exception):
    """Raised when required reference data is missing from the database.

    This indicates a server configuration issue - ESI/ESD data has not been
    synced properly.
    """

    def __init__(self, missing: str) -> None:
        self.missing = missing
        super().__init__(f"Missing reference data: {missing}")


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

# Propagation cache TTLs
USER_MAPS_CACHE_TTL = 120  # 2 minutes
PREVIOUS_STATE_TTL = 600  # 10 minutes


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


class _MapIdRow(msgspec.Struct):
    """Row for map ID query results."""

    id: UUID


class _NodeMapRow(msgspec.Struct):
    """Row for node/map lookup results."""

    node_id: UUID
    map_id: UUID


class CachedUserMaps(msgspec.Struct):
    """Cached list of maps a user has access to with location tracking enabled."""

    map_ids: list[str]
    fetched_at: float


class CachedPreviousState(msgspec.Struct):
    """Previous state for change detection - avoids duplicate events."""

    solar_system_id: int | None
    ship_type_id: int | None
    online: bool | None
    docked: bool
    fetched_at: float


@dataclass
class CharacterLocationData:
    """Combined location data for a character."""

    character_id: int
    character_name: str
    corporation_name: str | None
    alliance_name: str | None
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
    corporation_name: str | None
    alliance_name: str | None


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
        event_publisher: EventPublisher | None = None,
    ) -> None:
        self.db_session = db_session
        self.encryption_service = encryption_service
        self.sso_service = sso_service
        self.esi_client = esi_client
        self.cache = cache
        self.event_publisher = event_publisher

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

        Also clears location cache entries. Note: We can't emit CHARACTER_LEFT
        events here because we don't have user context for map access lookup.
        The character will disappear from nodes on next map load.

        Args:
            character_id: Character ID whose token should be deleted
        """
        logger.info("Invalidating revoked token for character %d", character_id)
        await self.db_session.execute(DELETE_REFRESH_TOKEN, character_id)

        # Clear location cache entries
        await self.cache.delete(f"{character_id}:position")
        await self.cache.delete(f"{character_id}:online")
        await self.cache.delete(f"{character_id}:ship")
        await self.cache.delete(f"char_prev_loc:{character_id}")

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

        Raises:
            ReferenceDataError: If required reference data is missing from the database.
                This indicates ESI/ESD data has not been synced properly.
        """
        system_name = await self._get_system_name(location.solar_system_id)
        if system_name is None:
            raise ReferenceDataError(f"solar_system:{location.solar_system_id}")

        ship_type_name: str | None = None
        if ship:
            ship_type_name = await self._get_ship_type_name(ship.ship_type_id)
            if ship_type_name is None:
                raise ReferenceDataError(f"ship_type:{ship.ship_type_id}")

        station_name: str | None = None
        if location.station_id:
            station_name = await self._get_station_name(location.station_id)
            if station_name is None:
                raise ReferenceDataError(f"station:{location.station_id}")

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
            corporation_name=char.corporation_name,
            alliance_name=char.alliance_name,
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
        try:
            names = await self._resolve_location_names(state.location, state.ship, access_token)
        except ReferenceDataError as e:
            logger.error("Missing reference data for character %d: %s", char.id, e.missing)
            return CharacterLocationError(character_id=char.id, character_name=char.name, error="server_error")

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

    # -------------------------------------------------------------------------
    # Location propagation (SSE events)
    # -------------------------------------------------------------------------

    async def get_user_accessible_maps(
        self,
        user_id: UUID,
        corporation_id: int | None,
        alliance_id: int | None,
    ) -> list[UUID]:
        """Get maps the user can access with location_tracking_enabled.

        Uses cache with 2-minute TTL.
        """
        cache_key = f"user_maps:{user_id}"
        cached = cast(bytes | None, await self.cache.get(cache_key))

        if cached:
            data = msgspec.json.decode(cached, type=CachedUserMaps)
            return [UUID(mid) for mid in data.map_ids]

        # Query database
        rows = await self.db_session.select(
            GET_USER_MAPS_WITH_LOCATION_TRACKING,
            user_id,
            corporation_id,
            alliance_id,
            schema_type=_MapIdRow,
        )
        map_ids = [row.id for row in rows]

        # Cache result
        cache_data = CachedUserMaps(
            map_ids=[str(mid) for mid in map_ids],
            fetched_at=time.time(),
        )
        await self.cache.setex(
            cache_key,
            USER_MAPS_CACHE_TTL,
            msgspec.json.encode(cache_data),
        )

        return map_ids

    async def get_previous_state(self, character_id: int) -> CachedPreviousState | None:
        """Get character's previous state from cache for change detection."""
        cache_key = f"char_prev_loc:{character_id}"
        cached = cast(bytes | None, await self.cache.get(cache_key))

        if cached:
            try:
                return msgspec.json.decode(cached, type=CachedPreviousState)
            except msgspec.DecodeError:
                return None
        return None

    async def set_previous_state(
        self,
        character_id: int,
        solar_system_id: int | None,
        ship_type_id: int | None,
        online: bool | None,
        docked: bool,
    ) -> None:
        """Store character's current state as previous for next comparison."""
        cache_key = f"char_prev_loc:{character_id}"
        data = CachedPreviousState(
            solar_system_id=solar_system_id,
            ship_type_id=ship_type_id,
            online=online,
            docked=docked,
            fetched_at=time.time(),
        )
        await self.cache.setex(
            cache_key,
            PREVIOUS_STATE_TTL,
            msgspec.json.encode(data),
        )

    async def propagate_location_change(
        self,
        user_id: UUID,
        corporation_id: int | None,
        alliance_id: int | None,
        character_name: str,
        corporation_name: str | None,
        alliance_name: str | None,
        previous_state: CachedPreviousState | None,
        current_system_id: int | None,
        current_ship_type_id: int | None,
        current_ship_type_name: str | None,
        current_online: bool | None,
        current_docked: bool,
    ) -> None:
        """Propagate location change to all relevant maps via SSE.

        Determines which event type to emit based on what changed:
        - System changed: CHARACTER_LEFT (old) + CHARACTER_ARRIVED (new)
        - Same system, other changes: CHARACTER_UPDATED
        - No changes: no events
        """
        if self.event_publisher is None:
            return

        previous_system_id = previous_state.solar_system_id if previous_state else None

        # Determine what changed
        system_changed = previous_system_id != current_system_id

        if previous_state is not None and not system_changed:
            # Same system - check if ship/online/docked changed
            ship_changed = previous_state.ship_type_id != current_ship_type_id
            online_changed = previous_state.online != current_online
            docked_changed = previous_state.docked != current_docked

            if not (ship_changed or online_changed or docked_changed):
                # Nothing changed - no events needed
                return

        # Get maps this user can access
        map_ids = await self.get_user_accessible_maps(user_id, corporation_id, alliance_id)
        if not map_ids:
            return

        char_location = NodeCharacterLocation(
            character_name=character_name,
            corporation_name=corporation_name,
            alliance_name=alliance_name,
            ship_type_name=current_ship_type_name,
            online=current_online,
            docked=current_docked,
        )

        if system_changed:
            # Emit "left" events for previous system
            if previous_system_id is not None:
                await self._emit_left_events(map_ids, previous_system_id, char_location)

            # Emit "arrived" events for current system
            if current_system_id is not None:
                await self._emit_arrived_events(map_ids, current_system_id, char_location)
        else:
            # Same system - emit "updated" events
            if current_system_id is not None:
                await self._emit_updated_events(map_ids, current_system_id, char_location)

    async def _emit_left_events(
        self,
        map_ids: list[UUID],
        system_id: int,
        char_location: NodeCharacterLocation,
    ) -> None:
        """Emit CHARACTER_LEFT events for nodes in the given system."""
        if self.event_publisher is None:
            return

        nodes = await self.db_session.select(
            GET_NODES_FOR_SYSTEM_IN_MAPS,
            system_id,
            map_ids,
            schema_type=_NodeMapRow,
        )

        for node in nodes:
            await self.event_publisher.character_left(
                map_id=node.map_id,
                node_id=node.node_id,
                character_data=char_location,
            )

    async def _emit_arrived_events(
        self,
        map_ids: list[UUID],
        system_id: int,
        char_location: NodeCharacterLocation,
    ) -> None:
        """Emit CHARACTER_ARRIVED events for nodes in the given system."""
        if self.event_publisher is None:
            return

        nodes = await self.db_session.select(
            GET_NODES_FOR_SYSTEM_IN_MAPS,
            system_id,
            map_ids,
            schema_type=_NodeMapRow,
        )

        for node in nodes:
            await self.event_publisher.character_arrived(
                map_id=node.map_id,
                node_id=node.node_id,
                character_data=char_location,
            )

    async def _emit_updated_events(
        self,
        map_ids: list[UUID],
        system_id: int,
        char_location: NodeCharacterLocation,
    ) -> None:
        """Emit CHARACTER_UPDATED events for nodes in the given system."""
        if self.event_publisher is None:
            return

        nodes = await self.db_session.select(
            GET_NODES_FOR_SYSTEM_IN_MAPS,
            system_id,
            map_ids,
            schema_type=_NodeMapRow,
        )

        for node in nodes:
            await self.event_publisher.character_updated(
                map_id=node.map_id,
                node_id=node.node_id,
                character_data=char_location,
            )

    async def invalidate_user_maps_cache(self, user_id: UUID) -> None:
        """Invalidate the user's accessible maps cache.

        Should be called when access control changes occur.
        """
        cache_key = f"user_maps:{user_id}"
        await self.cache.delete(cache_key)

    async def clear_character_location(
        self,
        character_id: int,
        character_name: str,
        corporation_name: str | None,
        alliance_name: str | None,
        user_id: UUID,
        corporation_id: int | None,
        alliance_id: int | None,
    ) -> None:
        """Clear character location cache and emit CHARACTER_LEFT if on a map.

        Called when:
        - Character is deleted
        - Location scope is removed

        Args:
            character_id: Character whose location to clear
            character_name: Character name for SSE event
            corporation_name: Corporation name for SSE event
            alliance_name: Alliance name for SSE event
            user_id: User ID for map access lookup
            corporation_id: Corporation ID for map access lookup
            alliance_id: Alliance ID for map access lookup
        """
        # Get previous state to know which system to emit leave from
        previous_state = await self.get_previous_state(character_id)

        # Clear all location cache entries
        await self.cache.delete(f"{character_id}:position")
        await self.cache.delete(f"{character_id}:online")
        await self.cache.delete(f"{character_id}:ship")
        await self.cache.delete(f"char_prev_loc:{character_id}")

        # Emit CHARACTER_LEFT if they had a cached location
        if previous_state and previous_state.solar_system_id and self.event_publisher:
            map_ids = await self.get_user_accessible_maps(user_id, corporation_id, alliance_id)
            if map_ids:
                char_location = NodeCharacterLocation(
                    character_name=character_name,
                    corporation_name=corporation_name,
                    alliance_name=alliance_name,
                    ship_type_name=None,
                    online=None,
                    docked=previous_state.docked,
                )
                await self._emit_left_events(map_ids, previous_state.solar_system_id, char_location)
