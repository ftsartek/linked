"""ESI route cache service.

Provides caching for ESI k-space route calculations. Routes are stored
in the database as they are essentially permanent (stargates don't change).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from database.models.esi_route_cache import INSERT_STMT, SELECT_STMT, ESIRouteCache
from utils.enums import RouteType

if TYPE_CHECKING:
    from sqlspec import AsyncDriverAdapterBase

    from esi_client.client import ESIClient

# Major trade hub system IDs for pre-fetching
TRADE_HUBS = [
    30000142,  # Jita
    30002187,  # Amarr
    30002659,  # Dodixie
    30002510,  # Rens
    30002053,  # Hek
]

# Query to get all k-space systems on a map
GET_MAP_KSPACE_SYSTEMS = """
SELECT DISTINCT s.id
FROM node n
JOIN system s ON n.system_id = s.id
WHERE n.map_id = $1
  AND n.date_deleted IS NULL
  AND n.system_id > 0
  AND (s.system_class IS NULL OR s.system_class IN (7, 8, 9));
"""


class RouteCacheService:
    """Service for caching ESI k-space routes."""

    def __init__(
        self,
        db_session: AsyncDriverAdapterBase,
        esi_client: ESIClient,
    ) -> None:
        self.db_session = db_session
        self.esi_client = esi_client

    async def get_cached_route(
        self,
        origin: int,
        destination: int,
        route_type: RouteType,
    ) -> ESIRouteCache | None:
        """Get a cached route from the database.

        Args:
            origin: Origin system ID
            destination: Destination system ID
            route_type: Type of route (shortest, secure, insecure)

        Returns:
            Cached route or None if not found
        """
        return await self.db_session.select_one_or_none(
            SELECT_STMT,
            origin,
            destination,
            route_type.value,
            schema_type=ESIRouteCache,
        )

    async def _fetch_and_cache_route(
        self,
        origin: int,
        destination: int,
        route_type: RouteType,
    ) -> ESIRouteCache:
        """Fetch a route from ESI and cache it in the database.

        Args:
            origin: Origin system ID
            destination: Destination system ID
            route_type: Type of route (shortest, secure, insecure)

        Returns:
            The cached route
        """
        # Fetch from ESI
        async with self.esi_client as client:
            waypoints = await client.get_route(
                origin=origin,
                destination=destination,
                flag=route_type.value,
            )

        # Store in database (upsert)
        return await self.db_session.select_one(
            INSERT_STMT,
            origin,
            destination,
            route_type.value,
            waypoints,
            len(waypoints) - 1,  # jump_count excludes origin
            schema_type=ESIRouteCache,
        )

    async def get_kspace_route(
        self,
        origin: int,
        destination: int,
        route_type: RouteType,
    ) -> list[int]:
        """Get a k-space route, checking database cache first.

        Args:
            origin: Origin system ID
            destination: Destination system ID
            route_type: Type of route (shortest, secure, insecure)

        Returns:
            List of system IDs representing the route
        """
        # Same system - no route needed
        if origin == destination:
            return [origin]

        # Check cache first
        cached = await self.get_cached_route(origin, destination, route_type)
        if cached is not None:
            return cached.waypoints

        # Fetch from ESI and cache
        route = await self._fetch_and_cache_route(origin, destination, route_type)
        return route.waypoints

    async def get_kspace_route_distance(
        self,
        origin: int,
        destination: int,
        route_type: RouteType,
    ) -> int:
        """Get the jump count for a k-space route.

        Args:
            origin: Origin system ID
            destination: Destination system ID
            route_type: Type of route (shortest, secure, insecure)

        Returns:
            Number of jumps (0 if same system)
        """
        if origin == destination:
            return 0

        cached = await self.get_cached_route(origin, destination, route_type)
        if cached is not None:
            return cached.jump_count

        route = await self._fetch_and_cache_route(origin, destination, route_type)
        return route.jump_count

    async def prefetch_routes_for_systems(
        self,
        system_ids: list[int],
        route_type: RouteType,
        include_trade_hubs: bool = True,
    ) -> int:
        """Pre-fetch routes between a set of systems.

        Args:
            system_ids: List of k-space system IDs to pre-fetch routes for
            route_type: Type of route to pre-fetch
            include_trade_hubs: Whether to also pre-fetch routes to trade hubs

        Returns:
            Number of routes fetched from ESI (not cached)
        """
        destinations = set(system_ids)
        if include_trade_hubs:
            destinations.update(TRADE_HUBS)

        fetched_count = 0

        for origin in system_ids:
            for destination in destinations:
                if origin == destination:
                    continue

                # Check if already cached
                cached = await self.get_cached_route(origin, destination, route_type)
                if cached is None:
                    await self._fetch_and_cache_route(origin, destination, route_type)
                    fetched_count += 1

        return fetched_count

    async def prefetch_map_routes(
        self,
        map_id: str,
        route_type: RouteType = RouteType.SHORTEST,
        include_trade_hubs: bool = True,
    ) -> int:
        """Pre-fetch routes for all k-space systems on a map.

        Args:
            map_id: Map UUID
            route_type: Type of route to pre-fetch
            include_trade_hubs: Whether to also pre-fetch routes to trade hubs

        Returns:
            Number of routes fetched from ESI (not cached)
        """
        # Get all k-space systems on the map
        result = await self.db_session.select(GET_MAP_KSPACE_SYSTEMS, [map_id])
        system_ids = [row["id"] for row in result]

        if not system_ids:
            return 0

        return await self.prefetch_routes_for_systems(
            system_ids=system_ids,
            route_type=route_type,
            include_trade_hubs=include_trade_hubs,
        )
