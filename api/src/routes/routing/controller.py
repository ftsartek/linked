"""Route calculation controller."""

from __future__ import annotations

from uuid import UUID

from litestar import Controller, Request, get
from litestar.di import Provide
from litestar.exceptions import ClientException, NotAuthorizedException, NotFoundException
from litestar.params import Parameter

from api.auth.guards import require_acl_access, require_auth
from routes.routing.dependencies import RouteResponse
from routes.routing.service import RoutingService, provide_routing_service
from utils.enums import RouteType

ERR_MAP_NO_ACCESS = "You do not have access to this map"


class RoutingController(Controller):
    """Route calculation endpoints."""

    path = "/routes"
    guards = [require_auth, require_acl_access]
    dependencies = {
        "routing_service": Provide(provide_routing_service),
    }

    @get("/{map_id:uuid}")
    async def calculate_route(
        self,
        request: Request,
        routing_service: RoutingService,
        map_id: UUID,
        origin: UUID = Parameter(query="origin", description="Origin node ID on the map"),
        destination: int = Parameter(query="destination", description="Destination system ID"),
        route_type: str = Parameter(
            query="route_type",
            default="shortest",
            description="Route type: shortest, secure",
        ),
    ) -> RouteResponse:
        """Calculate a route from a node on the map to a destination system.

        The destination can be any k-space system, whether on the chain or not.
        For off-chain destinations, the route will find the best exit point.

        Route types:
        - shortest: Minimum total jumps
        - secure: Prefer high-sec k-space, penalize wormhole jumps
        """
        ctx = await routing_service.get_character_context(request.user.id)

        has_access = await routing_service.can_access_map(
            map_id=map_id,
            user_id=ctx.user_id,
            corporation_id=ctx.corporation_id,
            alliance_id=ctx.alliance_id,
        )
        if not has_access:
            raise NotAuthorizedException(ERR_MAP_NO_ACCESS)

        # Validate route type
        try:
            route_type_enum = RouteType(route_type)
        except ValueError:
            raise ClientException(f"Invalid route_type: {route_type}. Must be one of: shortest, secure") from None

        result = await routing_service.calculate_route(
            map_id=map_id,
            origin_node_id=origin,
            destination_system_id=destination,
            route_type=route_type_enum,
        )

        if result is None:
            raise NotFoundException("No route found. Origin node may not exist or destination is unreachable.")

        return result
