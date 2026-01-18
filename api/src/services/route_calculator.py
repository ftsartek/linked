"""Route calculation service using Dijkstra's algorithm.

Calculates routes through the wormhole chain, combining on-chain
wormhole connections with ESI k-space routes.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from uuid import UUID

import msgspec

from services.route_cache import RouteCacheService
from utils.enums import RouteType

if TYPE_CHECKING:
    from sqlspec import AsyncDriverAdapterBase

    from esi_client.client import ESIClient

# System class values for k-space
KSPACE_CLASSES = {7, 8, 9}  # HS, LS, NS
# System class 25 is Pochven (no stargates, treated as w-space for routing)

# Weight multipliers for safest route calculation
# These are heavily skewed to avoid dangerous space unless absolutely necessary
WEIGHT_HIGHSEC = 1
WEIGHT_LOWSEC = 100
WEIGHT_NULLSEC = 200
WEIGHT_WORMHOLE_JUMP = 100

# Query to get nodes with system class info
GET_MAP_NODES_FOR_ROUTING = """
SELECT
    n.id AS node_id,
    n.system_id,
    s.system_class,
    s.security_status
FROM node n
JOIN system s ON n.system_id = s.id
WHERE n.map_id = $1
  AND n.date_deleted IS NULL
  AND n.system_id > 0;
"""

# Query to get links for routing
GET_MAP_LINKS_FOR_ROUTING = """
SELECT
    l.source_node_id,
    l.target_node_id
FROM link l
WHERE l.map_id = $1
  AND l.date_deleted IS NULL;
"""

# Query to check if a system is k-space
GET_SYSTEM_INFO = """
SELECT id, system_class, security_status
FROM system
WHERE id = $1;
"""


@dataclass
class NodeInfo:
    """Node information for routing."""

    node_id: UUID
    system_id: int
    system_class: int | None
    security_status: float | None

    @property
    def is_kspace(self) -> bool:
        """Check if this node is in k-space."""
        return self.system_class is None or self.system_class in KSPACE_CLASSES

    @property
    def is_wspace(self) -> bool:
        """Check if this node is in w-space (including Pochven)."""
        return not self.is_kspace


class RouteWaypoint(msgspec.Struct):
    """A single waypoint in a calculated route."""

    system_id: int
    node_id: UUID | None = None  # None if system is off-chain
    is_wormhole_jump: bool = False  # True if arrived via wormhole


class RouteResult(msgspec.Struct):
    """Result of a route calculation."""

    waypoints: list[RouteWaypoint]
    total_jumps: int
    wormhole_jumps: int
    kspace_jumps: int
    destination_on_chain: bool
    route_type: RouteType


@dataclass
class _ExtendedEdge:
    """Edge in the extended routing graph.

    Represents either a wormhole connection or a virtual k-space bridge.
    """

    target_node_id: UUID
    weight: float
    is_wormhole: bool
    kspace_route: list[int] | None = None  # Full route for k-space edges (includes endpoints)


@dataclass
class _DijkstraNode:
    """Internal node for Dijkstra's algorithm priority queue."""

    cost: float
    node_id: UUID
    path: list[tuple[UUID, bool, list[int] | None]] = field(default_factory=list)  # (node_id, is_wh_jump, kspace_route)

    def __lt__(self, other: _DijkstraNode) -> bool:
        return self.cost < other.cost


# Performance limits for k-space bridge calculations
MAX_KSPACE_BRIDGE_JUMPS = 30  # Skip bridges longer than this
MAX_KSPACE_PAIRS = 50  # Maximum number of k-space pairs to consider


class RouteCalculatorService:
    """Service for calculating routes through wormhole chains."""

    def __init__(
        self,
        db_session: AsyncDriverAdapterBase,
        esi_client: ESIClient,
    ) -> None:
        self.db_session = db_session
        self.route_cache = RouteCacheService(db_session, esi_client)

    async def _load_map_graph(
        self,
        map_id: UUID,
    ) -> tuple[dict[UUID, NodeInfo], dict[UUID, set[UUID]]]:
        """Load nodes and links for a map.

        Returns:
            Tuple of (nodes dict by node_id, adjacency dict)
        """
        # Load nodes
        node_rows = await self.db_session.select(GET_MAP_NODES_FOR_ROUTING, [map_id])
        nodes: dict[UUID, NodeInfo] = {}
        for row in node_rows:
            nodes[row["node_id"]] = NodeInfo(
                node_id=row["node_id"],
                system_id=row["system_id"],
                system_class=row["system_class"],
                security_status=row["security_status"],
            )

        # Load links (bidirectional)
        link_rows = await self.db_session.select(GET_MAP_LINKS_FOR_ROUTING, [map_id])
        adjacency: dict[UUID, set[UUID]] = {node_id: set() for node_id in nodes}
        for row in link_rows:
            source = row["source_node_id"]
            target = row["target_node_id"]
            if source in adjacency and target in adjacency:
                adjacency[source].add(target)
                adjacency[target].add(source)

        return nodes, adjacency

    def _get_edge_weight(
        self,
        to_node: NodeInfo,
        route_type: RouteType,
        is_wormhole_edge: bool,
    ) -> float:
        """Calculate edge weight based on route type.

        Args:
            to_node: Destination node
            route_type: Type of route calculation
            is_wormhole_edge: Whether this edge is a wormhole connection

        Returns:
            Edge weight
        """
        if route_type == RouteType.SHORTEST:
            return 1.0

        # Safest route - penalize based on system type
        if is_wormhole_edge:
            return WEIGHT_WORMHOLE_JUMP

        # K-space edge weight based on security
        if to_node.security_status is not None:
            if to_node.security_status >= 0.5:
                return WEIGHT_HIGHSEC
            if to_node.security_status > 0.0:
                return WEIGHT_LOWSEC
            return WEIGHT_NULLSEC

        return 1.0

    async def _get_kspace_distance(
        self,
        from_system: int,
        to_system: int,
        route_type: RouteType,
    ) -> int:
        """Get the distance between two k-space systems.

        Maps RouteType to ESI flag:
        - SHORTEST -> shortest
        - SECURE -> secure
        """
        esi_route_type = RouteType.SECURE if route_type == RouteType.SECURE else RouteType.SHORTEST

        return await self.route_cache.get_kspace_route_distance(
            from_system,
            to_system,
            esi_route_type,
        )

    async def _get_kspace_route(
        self,
        from_system: int,
        to_system: int,
        route_type: RouteType,
    ) -> list[int]:
        """Get the full route between two k-space systems.

        Returns:
            List of system IDs representing the route (includes both endpoints)
        """
        esi_route_type = RouteType.SECURE if route_type == RouteType.SECURE else RouteType.SHORTEST

        return await self.route_cache.get_kspace_route(
            from_system,
            to_system,
            esi_route_type,
        )

    def _calculate_kspace_weight(
        self,
        jump_count: int,
        route_type: RouteType,
    ) -> float:
        """Calculate weight for a k-space travel segment.

        Args:
            jump_count: Number of k-space jumps
            route_type: Type of route calculation

        Returns:
            Weighted cost for the k-space segment
        """
        if route_type == RouteType.SHORTEST:
            return float(jump_count)

        # For SECURE, use average highsec weight (ESI secure routes prefer highsec)
        return float(jump_count) * WEIGHT_HIGHSEC

    async def _build_extended_graph(
        self,
        nodes: dict[UUID, NodeInfo],
        adjacency: dict[UUID, set[UUID]],
        kspace_nodes: list[NodeInfo],
        route_type: RouteType,
    ) -> dict[UUID, list[_ExtendedEdge]]:
        """Build extended graph with virtual k-space edges.

        Converts the basic adjacency structure to extended edges and adds
        virtual k-space bridge edges between all k-space node pairs.

        Args:
            nodes: All nodes on the map
            adjacency: Basic wormhole adjacency structure
            kspace_nodes: List of k-space nodes for bridge calculation
            route_type: Type of route calculation

        Returns:
            Extended adjacency structure with both wormhole and k-space edges
        """
        extended_adj: dict[UUID, list[_ExtendedEdge]] = {node_id: [] for node_id in nodes}

        # Convert existing wormhole edges
        for node_id, neighbors in adjacency.items():
            for neighbor_id in neighbors:
                neighbor = nodes[neighbor_id]
                weight = self._get_edge_weight(neighbor, route_type, is_wormhole_edge=True)
                extended_adj[node_id].append(
                    _ExtendedEdge(
                        target_node_id=neighbor_id,
                        weight=weight,
                        is_wormhole=True,
                        kspace_route=None,
                    )
                )

        # Add virtual k-space bridge edges between k-space node pairs
        # Limit pairs for performance
        pairs_added = 0
        for i, node1 in enumerate(kspace_nodes):
            if pairs_added >= MAX_KSPACE_PAIRS:
                break
            for node2 in kspace_nodes[i + 1 :]:
                if pairs_added >= MAX_KSPACE_PAIRS:
                    break

                try:
                    # Get the full k-space route between these systems
                    kspace_route = await self._get_kspace_route(
                        node1.system_id,
                        node2.system_id,
                        route_type,
                    )
                    jump_count = len(kspace_route) - 1

                    # Skip bridges that are too long
                    if jump_count > MAX_KSPACE_BRIDGE_JUMPS:
                        continue

                    weight = self._calculate_kspace_weight(jump_count, route_type)

                    # Add bidirectional edges
                    extended_adj[node1.node_id].append(
                        _ExtendedEdge(
                            target_node_id=node2.node_id,
                            weight=weight,
                            is_wormhole=False,
                            kspace_route=kspace_route,
                        )
                    )
                    extended_adj[node2.node_id].append(
                        _ExtendedEdge(
                            target_node_id=node1.node_id,
                            weight=weight,
                            is_wormhole=False,
                            kspace_route=list(reversed(kspace_route)),
                        )
                    )
                    pairs_added += 1
                except Exception:
                    # ESI route failed (no route exists, isolated systems, etc.)
                    continue

        return extended_adj

    async def _dijkstra_extended(
        self,
        nodes: dict[UUID, NodeInfo],
        extended_adj: dict[UUID, list[_ExtendedEdge]],
        origin_id: UUID,
        dest_id: UUID | None,
        destination_system_id: int,
        route_type: RouteType,
    ) -> RouteResult | None:
        """Run Dijkstra on extended graph with k-space bridge support.

        Args:
            nodes: All nodes on the map
            extended_adj: Extended adjacency with wormhole and k-space edges
            origin_id: Starting node UUID
            dest_id: Destination node UUID (None if off-chain)
            destination_system_id: Target system ID
            route_type: Type of route calculation

        Returns:
            RouteResult with waypoints, or None if no route found
        """
        # For off-chain destinations, we'll track the best route to any k-space exit
        # and then add the ESI route from that exit to the destination
        destination_on_chain = dest_id is not None

        visited: set[UUID] = set()
        # path entries: (node_id, is_wormhole_jump, kspace_route_if_bridge)
        pq: list[_DijkstraNode] = [_DijkstraNode(cost=0, node_id=origin_id, path=[(origin_id, False, None)])]

        # For off-chain: track best route to each k-space exit + ESI distance to destination
        best_off_chain_result: RouteResult | None = None
        best_off_chain_cost: float = float("inf")

        while pq:
            current = heapq.heappop(pq)

            if current.node_id in visited:
                continue
            visited.add(current.node_id)

            current_node = nodes[current.node_id]

            # Check if we've reached the destination (on-chain case)
            if destination_on_chain and current.node_id == dest_id:
                return self._build_route_result(nodes, current.path, route_type, destination_on_chain=True)

            # For off-chain destinations, check if this k-space node offers a better route
            if not destination_on_chain and current_node.is_kspace:
                try:
                    kspace_distance = await self._get_kspace_distance(
                        current_node.system_id,
                        destination_system_id,
                        route_type,
                    )
                    kspace_weight = self._calculate_kspace_weight(kspace_distance, route_type)
                    total_cost = current.cost + kspace_weight

                    if total_cost < best_off_chain_cost:
                        best_off_chain_cost = total_cost

                        # Get the full k-space route for waypoint expansion
                        kspace_route = await self._get_kspace_route(
                            current_node.system_id,
                            destination_system_id,
                            route_type,
                        )

                        best_off_chain_result = self._build_route_result(
                            nodes,
                            current.path,
                            route_type,
                            destination_on_chain=False,
                            final_kspace_route=kspace_route,
                        )
                except Exception:
                    # No ESI route to destination from this exit
                    pass

            # Explore neighbors via extended edges
            for edge in extended_adj.get(current.node_id, []):
                if edge.target_node_id in visited:
                    continue

                new_cost = current.cost + edge.weight
                new_path = current.path + [(edge.target_node_id, edge.is_wormhole, edge.kspace_route)]

                heapq.heappush(
                    pq,
                    _DijkstraNode(cost=new_cost, node_id=edge.target_node_id, path=new_path),
                )

        # Return best off-chain result if we found one
        if not destination_on_chain and best_off_chain_result is not None:
            return best_off_chain_result

        return None

    def _build_route_result(
        self,
        nodes: dict[UUID, NodeInfo],
        path: list[tuple[UUID, bool, list[int] | None]],
        route_type: RouteType,
        destination_on_chain: bool,
        final_kspace_route: list[int] | None = None,
    ) -> RouteResult:
        """Build RouteResult from a path with potential k-space bridges.

        Args:
            nodes: All nodes on the map
            path: List of (node_id, is_wormhole_jump, kspace_route) tuples
            route_type: Type of route calculation
            destination_on_chain: Whether destination is on the chain
            final_kspace_route: For off-chain destinations, the final ESI route

        Returns:
            RouteResult with expanded waypoints
        """
        waypoints: list[RouteWaypoint] = []
        wormhole_jumps = 0
        kspace_jumps = 0

        for i, (node_id, is_wh_jump, kspace_route) in enumerate(path):
            node = nodes[node_id]

            # If this step used a k-space bridge, insert intermediate waypoints
            if kspace_route is not None and i > 0:
                # kspace_route includes both endpoints; skip first (already in waypoints)
                # and last (will be added as the node waypoint)
                for sys_id in kspace_route[1:-1]:
                    waypoints.append(
                        RouteWaypoint(
                            system_id=sys_id,
                            node_id=None,
                            is_wormhole_jump=False,
                        )
                    )
                kspace_jumps += len(kspace_route) - 1

            # Add the node waypoint
            waypoints.append(
                RouteWaypoint(
                    system_id=node.system_id,
                    node_id=node_id,
                    is_wormhole_jump=is_wh_jump,
                )
            )

            if is_wh_jump:
                wormhole_jumps += 1

        # For off-chain destinations, add the final k-space segment
        if final_kspace_route is not None and len(final_kspace_route) > 1:
            # Skip first system (already the last node waypoint)
            for sys_id in final_kspace_route[1:]:
                waypoints.append(
                    RouteWaypoint(
                        system_id=sys_id,
                        node_id=None,
                        is_wormhole_jump=False,
                    )
                )
            kspace_jumps += len(final_kspace_route) - 1

        total_jumps = len(waypoints) - 1

        return RouteResult(
            waypoints=waypoints,
            total_jumps=total_jumps,
            wormhole_jumps=wormhole_jumps,
            kspace_jumps=kspace_jumps,
            destination_on_chain=destination_on_chain,
            route_type=route_type,
        )

    async def calculate_route(
        self,
        map_id: UUID,
        origin_node_id: UUID,
        destination_system_id: int,
        route_type: RouteType = RouteType.SHORTEST,
    ) -> RouteResult | None:
        """Calculate a route from a node on the map to a destination system.

        The destination can be:
        - A system already on the chain (another node)
        - Any k-space system (will find the best exit point)

        This method supports k-space bridging: exiting the chain through one
        k-space connection, traveling through k-space, and re-entering through
        a different k-space connection when that provides a shorter route.

        Args:
            map_id: The map UUID
            origin_node_id: Starting node on the map
            destination_system_id: Target system ID
            route_type: Type of route (shortest, secure)

        Returns:
            RouteResult with waypoints, or None if no route exists
        """
        # Load the map graph
        nodes, adjacency = await self._load_map_graph(map_id)

        if origin_node_id not in nodes:
            return None

        # Check if destination is already on the chain
        dest_node_id: UUID | None = None
        for node_id, node in nodes.items():
            if node.system_id == destination_system_id:
                dest_node_id = node_id
                break

        # Identify k-space nodes for potential bridging
        kspace_nodes = [node for node in nodes.values() if node.is_kspace]

        # If fewer than 2 k-space nodes, bridging isn't possible
        # Fall back to original behavior for simplicity
        if len(kspace_nodes) < 2:
            if dest_node_id is not None:
                return await self._calculate_on_chain_route(
                    nodes,
                    adjacency,
                    origin_node_id,
                    dest_node_id,
                    route_type,
                )
            return await self._calculate_off_chain_route(
                nodes,
                adjacency,
                origin_node_id,
                destination_system_id,
                route_type,
            )

        # Build extended graph with virtual k-space bridge edges
        extended_adj = await self._build_extended_graph(
            nodes,
            adjacency,
            kspace_nodes,
            route_type,
        )

        # Run unified Dijkstra on extended graph
        return await self._dijkstra_extended(
            nodes,
            extended_adj,
            origin_node_id,
            dest_node_id,
            destination_system_id,
            route_type,
        )

    async def _calculate_on_chain_route(
        self,
        nodes: dict[UUID, NodeInfo],
        adjacency: dict[UUID, set[UUID]],
        origin_id: UUID,
        dest_id: UUID,
        route_type: RouteType,
    ) -> RouteResult | None:
        """Calculate route between two nodes on the same chain.

        This is the fallback method used when k-space bridging is not possible
        (fewer than 2 k-space nodes on the chain).
        """
        # Dijkstra's algorithm
        visited: set[UUID] = set()
        pq: list[_DijkstraNode] = [_DijkstraNode(cost=0, node_id=origin_id, path=[(origin_id, False, None)])]

        while pq:
            current = heapq.heappop(pq)

            if current.node_id in visited:
                continue
            visited.add(current.node_id)

            if current.node_id == dest_id:
                # Build result using the shared helper
                return self._build_route_result(nodes, current.path, route_type, destination_on_chain=True)

            for neighbor_id in adjacency[current.node_id]:
                if neighbor_id in visited:
                    continue

                neighbor = nodes[neighbor_id]
                # All edges on the chain are wormhole edges
                weight = self._get_edge_weight(
                    neighbor,
                    route_type,
                    is_wormhole_edge=True,
                )
                new_cost = current.cost + weight
                new_path = current.path + [(neighbor_id, True, None)]

                heapq.heappush(
                    pq,
                    _DijkstraNode(cost=new_cost, node_id=neighbor_id, path=new_path),
                )

        return None  # No route found

    async def _calculate_off_chain_route(
        self,
        nodes: dict[UUID, NodeInfo],
        adjacency: dict[UUID, set[UUID]],
        origin_id: UUID,
        destination_system_id: int,
        route_type: RouteType,
    ) -> RouteResult | None:
        """Calculate route from a node to an off-chain k-space destination.

        Finds the best k-space exit point and combines with ESI route.
        """
        # Find all k-space nodes (potential exit points)
        kspace_exits: list[tuple[UUID, int]] = [
            (node_id, node.system_id) for node_id, node in nodes.items() if node.is_kspace
        ]

        if not kspace_exits:
            # No k-space exits on chain - can't reach destination
            return None

        # Calculate route to each exit + ESI route from exit to destination
        best_route: RouteResult | None = None
        best_total_cost: float = float("inf")

        for exit_node_id, exit_system_id in kspace_exits:
            # Calculate on-chain route to this exit
            chain_route = await self._calculate_on_chain_route(
                nodes,
                adjacency,
                origin_id,
                exit_node_id,
                route_type,
            )

            if chain_route is None:
                continue

            # Get ESI route from exit to destination
            try:
                kspace_distance = await self._get_kspace_distance(
                    exit_system_id,
                    destination_system_id,
                    route_type,
                )
            except Exception:
                # ESI route failed - skip this exit
                continue

            # Calculate total cost
            # For off-chain, we add the k-space distance
            total_jumps = chain_route.total_jumps + kspace_distance

            # Simple cost calculation for comparison
            if route_type == RouteType.SHORTEST:
                total_cost = total_jumps
            else:
                # For safest, weight wormhole jumps more heavily
                total_cost = (
                    chain_route.wormhole_jumps * WEIGHT_WORMHOLE_JUMP
                    + kspace_distance * WEIGHT_HIGHSEC  # Assume avg k-space cost
                )

            if total_cost < best_total_cost:
                best_total_cost = total_cost

                # Get the full k-space route for waypoint expansion
                try:
                    kspace_route = await self._get_kspace_route(
                        exit_system_id,
                        destination_system_id,
                        route_type,
                    )
                except Exception:
                    # Fallback: just add the destination if route fetch fails
                    kspace_route = [exit_system_id, destination_system_id]

                # Build combined route with expanded k-space waypoints
                waypoints = list(chain_route.waypoints)

                # Add intermediate k-space systems (skip first, it's already the exit node)
                for sys_id in kspace_route[1:]:
                    waypoints.append(
                        RouteWaypoint(
                            system_id=sys_id,
                            node_id=None,
                            is_wormhole_jump=False,
                        )
                    )

                best_route = RouteResult(
                    waypoints=waypoints,
                    total_jumps=total_jumps,
                    wormhole_jumps=chain_route.wormhole_jumps,
                    kspace_jumps=chain_route.kspace_jumps + kspace_distance,
                    destination_on_chain=False,
                    route_type=route_type,
                )

        return best_route

    async def calculate_route_between_systems(
        self,
        map_id: UUID,
        origin_system_id: int,
        destination_system_id: int,
        route_type: RouteType = RouteType.SHORTEST,
    ) -> RouteResult | None:
        """Calculate a route between two systems (finding origin node automatically).

        Args:
            map_id: The map UUID
            origin_system_id: Starting system ID (must be on the map)
            destination_system_id: Target system ID
            route_type: Type of route (shortest, secure)

        Returns:
            RouteResult with waypoints, or None if no route exists
        """
        # Load the map graph
        nodes, adjacency = await self._load_map_graph(map_id)

        # Find origin node
        origin_node_id: UUID | None = None
        for node_id, node in nodes.items():
            if node.system_id == origin_system_id:
                origin_node_id = node_id
                break

        if origin_node_id is None:
            return None  # Origin not on map

        return await self.calculate_route(
            map_id,
            origin_node_id,
            destination_system_id,
            route_type,
        )
