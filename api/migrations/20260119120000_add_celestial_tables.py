"""Add celestial object tables
Description: Add tables for stargates, stars, planets, moons, asteroid belts, and NPC stations
Version: 20260119120000
Created: 2026-01-19T12:00:00.000000+00:00
Author: Jordan Russell <jordan@artek.nz>"""

from collections.abc import Iterable


async def up(context: object | None = None) -> str | Iterable[str]:
    """Apply the migration (upgrade)."""
    return [
        # Star table
        """\
CREATE TABLE IF NOT EXISTS star (
    id INTEGER PRIMARY KEY,
    system_id INTEGER NOT NULL REFERENCES system(id) ON DELETE CASCADE,
    type_id INTEGER,
    type_name TEXT,
    radius REAL,
    age REAL,
    life REAL,
    luminosity REAL,
    spectral_class TEXT,
    temperature REAL
);
""",
        "CREATE INDEX IF NOT EXISTS idx_star_system_id ON star(system_id);",
        # Planet table
        """\
CREATE TABLE IF NOT EXISTS planet (
    id INTEGER PRIMARY KEY,
    system_id INTEGER NOT NULL REFERENCES system(id) ON DELETE CASCADE,
    type_id INTEGER,
    type_name TEXT,
    celestial_index INTEGER,
    radius REAL,
    orbit_id INTEGER,
    pos_x REAL,
    pos_y REAL,
    pos_z REAL
);
""",
        "CREATE INDEX IF NOT EXISTS idx_planet_system_id ON planet(system_id);",
        "CREATE INDEX IF NOT EXISTS idx_planet_celestial_index ON planet(celestial_index);",
        # Moon table
        """\
CREATE TABLE IF NOT EXISTS moon (
    id INTEGER PRIMARY KEY,
    system_id INTEGER NOT NULL REFERENCES system(id) ON DELETE CASCADE,
    planet_id INTEGER REFERENCES planet(id) ON DELETE SET NULL,
    type_id INTEGER,
    type_name TEXT,
    celestial_index INTEGER,
    orbit_index INTEGER,
    radius REAL,
    pos_x REAL,
    pos_y REAL,
    pos_z REAL
);
""",
        "CREATE INDEX IF NOT EXISTS idx_moon_system_id ON moon(system_id);",
        "CREATE INDEX IF NOT EXISTS idx_moon_planet_id ON moon(planet_id);",
        # Asteroid belt table
        """\
CREATE TABLE IF NOT EXISTS asteroid_belt (
    id INTEGER PRIMARY KEY,
    system_id INTEGER NOT NULL REFERENCES system(id) ON DELETE CASCADE,
    planet_id INTEGER REFERENCES planet(id) ON DELETE SET NULL,
    type_id INTEGER,
    type_name TEXT,
    celestial_index INTEGER,
    orbit_index INTEGER,
    radius REAL,
    pos_x REAL,
    pos_y REAL,
    pos_z REAL
);
""",
        "CREATE INDEX IF NOT EXISTS idx_asteroid_belt_system_id ON asteroid_belt(system_id);",
        "CREATE INDEX IF NOT EXISTS idx_asteroid_belt_planet_id ON asteroid_belt(planet_id);",
        # Stargate table (destination FK added separately to avoid circular issues)
        """\
CREATE TABLE IF NOT EXISTS stargate (
    id INTEGER PRIMARY KEY,
    system_id INTEGER NOT NULL REFERENCES system(id) ON DELETE CASCADE,
    destination_stargate_id INTEGER,
    destination_system_id INTEGER REFERENCES system(id),
    type_id INTEGER,
    type_name TEXT,
    pos_x REAL,
    pos_y REAL,
    pos_z REAL
);
""",
        "CREATE INDEX IF NOT EXISTS idx_stargate_system_id ON stargate(system_id);",
        "CREATE INDEX IF NOT EXISTS idx_stargate_destination_system_id ON stargate(destination_system_id);",
        # NPC station table
        """\
CREATE TABLE IF NOT EXISTS npc_station (
    id INTEGER PRIMARY KEY,
    system_id INTEGER NOT NULL REFERENCES system(id) ON DELETE CASCADE,
    type_id INTEGER,
    type_name TEXT,
    owner_id INTEGER,
    celestial_index INTEGER,
    orbit_id INTEGER,
    orbit_index INTEGER,
    operation_id INTEGER,
    reprocessing_efficiency REAL,
    reprocessing_stations_take REAL,
    pos_x REAL,
    pos_y REAL,
    pos_z REAL
);
""",
        "CREATE INDEX IF NOT EXISTS idx_npc_station_system_id ON npc_station(system_id);",
        "CREATE INDEX IF NOT EXISTS idx_npc_station_owner_id ON npc_station(owner_id);",
    ]


async def down(context: object | None = None) -> str | Iterable[str]:
    """Reverse the migration."""
    return [
        "DROP TABLE IF EXISTS npc_station CASCADE;",
        "DROP TABLE IF EXISTS stargate CASCADE;",
        "DROP TABLE IF EXISTS asteroid_belt CASCADE;",
        "DROP TABLE IF EXISTS moon CASCADE;",
        "DROP TABLE IF EXISTS planet CASCADE;",
        "DROP TABLE IF EXISTS star CASCADE;",
    ]
