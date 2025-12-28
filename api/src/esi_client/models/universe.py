from __future__ import annotations

from msgspec import Struct


class Position(Struct):
    x: float
    y: float
    z: float


class Planet(Struct):
    planet_id: int
    asteroid_belts: list[int] | None = None
    moons: list[int] | None = None


class Region(Struct):
    region_id: int
    name: str
    constellations: list[int]
    description: str | None = None


class Constellation(Struct):
    constellation_id: int
    name: str
    region_id: int
    systems: list[int]
    position: Position


class System(Struct):
    system_id: int
    name: str
    constellation_id: int
    security_status: float
    position: Position
    security_class: str | None = None
    star_id: int | None = None
    stargates: list[int] | None = None
    stations: list[int] | None = None
    planets: list[Planet] | None = None
