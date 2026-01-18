"""Routing service for route calculation endpoints."""

from __future__ import annotations

from uuid import UUID

from sqlspec import AsyncDriverAdapterBase

from config import get_settings
from esi_client.client import ESIClient
from routes.routing.dependencies import RouteResponse, RouteWaypointInfo
from services.route_base import RouteBaseService
from services.route_calculator import RouteCalculatorService
from utils.class_mapping import SYSTEM_CLASS_MAPPING
from utils.enums import RouteType

# Query to get system info by ID
GET_SYSTEM_INFO = """
SELECT name, system_class, security_status FROM system WHERE id = $1;
"""


class RoutingService(RouteBaseService):
    """Routing business logic."""

    async def calculate_route(
        self,
        map_id: UUID,
        origin_node_id: UUID,
        destination_system_id: int,
        route_type: RouteType,
    ) -> RouteResponse | None:
        """Calculate a route and enrich with system information.

        Returns None if no route found or origin doesn't exist.
        """
        # Create route calculator with ESI client
        settings = get_settings()
        esi_client = ESIClient(settings.esi.user_agent, settings.esi.timeout)
        route_calculator = RouteCalculatorService(self.db_session, esi_client)

        result = await route_calculator.calculate_route(
            map_id=map_id,
            origin_node_id=origin_node_id,
            destination_system_id=destination_system_id,
            route_type=route_type,
        )

        if result is None:
            return None

        # Enrich waypoints with system names and class info
        waypoints = []
        for wp in result.waypoints:
            system_info = await self.db_session.select_one_or_none(
                GET_SYSTEM_INFO,
                wp.system_id,
            )
            system_name = system_info["name"] if system_info else None
            system_class = system_info["system_class"] if system_info else None
            security_status = system_info["security_status"] if system_info else None
            class_name = SYSTEM_CLASS_MAPPING.get(system_class) if system_class is not None else None

            waypoints.append(
                RouteWaypointInfo(
                    system_id=wp.system_id,
                    system_name=system_name,
                    class_name=class_name,
                    security_status=security_status,
                    node_id=wp.node_id,
                    is_wormhole_jump=wp.is_wormhole_jump,
                )
            )

        return RouteResponse(
            waypoints=waypoints,
            total_jumps=result.total_jumps,
            wormhole_jumps=result.wormhole_jumps,
            kspace_jumps=result.kspace_jumps,
            destination_on_chain=result.destination_on_chain,
            route_type=result.route_type.value,
        )


async def provide_routing_service(db_session: AsyncDriverAdapterBase) -> RoutingService:
    """Provide RoutingService with injected database session."""
    return RoutingService(db_session)
