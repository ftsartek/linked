"""Msgspec structs and types for routing endpoints."""

from __future__ import annotations

from uuid import UUID

import msgspec


class RouteWaypointInfo(msgspec.Struct):
    """A single waypoint in a calculated route."""

    system_id: int
    system_name: str | None = None  # Populated for display
    class_name: str | None = None  # System class (C1-C6, HS, LS, NS, etc.)
    node_id: UUID | None = None  # None if system is off-chain
    is_wormhole_jump: bool = False  # True if arrived via wormhole


class RouteResponse(msgspec.Struct):
    """Response for route calculation."""

    waypoints: list[RouteWaypointInfo]
    total_jumps: int
    wormhole_jumps: int
    kspace_jumps: int
    destination_on_chain: bool
    route_type: str  # shortest, secure
