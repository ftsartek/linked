"""Curated preseed data for tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlspec.adapters.asyncpg.driver import AsyncpgDriver


async def preseed_test_data(session: AsyncpgDriver) -> None:
    """Insert curated test data into the database.

    This creates a minimal but realistic dataset for testing:
    - Wormhole types (K162 with 24hr lifetime is critical for lifecycle tests)
    - Regions, constellations, and systems including both k-space and w-space
    - Effects for wormhole systems
    - System statics
    """
    # 1. Insert effects
    await session.execute(
        """
        INSERT INTO effect (id, name, buffs, debuffs) VALUES
        (1, 'Black Hole', '{"missile_velocity": 100}', '{"inertia": 100}'),
        (2, 'Magnetar', '{"damage": 100}', '{"tracking": 50}')
        ON CONFLICT (id) DO NOTHING
        """
    )

    # 2. Insert regions
    await session.execute(
        """
        INSERT INTO region (id, name) VALUES
        (10000002, 'The Forge'),
        (11000001, 'A-R00001'),
        (11000002, 'B-R00002')
        ON CONFLICT (id) DO NOTHING
        """
    )

    # 3. Insert constellations
    await session.execute(
        """
        INSERT INTO constellation (id, region_id, name) VALUES
        (20000020, 10000002, 'Kimotoro'),
        (21000001, 11000001, 'A-C00001'),
        (21000002, 11000002, 'B-C00001')
        ON CONFLICT (id) DO NOTHING
        """
    )

    # 4. Insert wormhole types (K162 is critical for lifecycle tests - 24hr lifetime)
    await session.execute(
        """
        INSERT INTO wormhole (id, code, lifetime, mass_total, mass_jump_max, target_class) VALUES
        (1, 'K162', 24.0, 2000000000, 300000000, NULL),
        (2, 'C140', 24.0, 3000000000, 300000000, 0),
        (3, 'N944', 24.0, 3000000000, 300000000, 5),
        (4, 'H296', 16.0, 3000000000, 300000000, 5)
        ON CONFLICT (id) DO NOTHING
        """
    )

    # 5. Insert systems
    # Includes:
    # - Jita (30000142) - Famous trade hub in The Forge
    # - Perimeter (30000144) - Adjacent to Jita
    # - J123456 (31000001) - Test C3 wormhole with Black Hole effect
    # - J234567 (31000002) - Test C5 wormhole with Magnetar effect
    # - J345678 (31000003) - Test C3 wormhole without effect
    # - Unidentified placeholders for each class (negative IDs)
    await session.execute(
        """
        INSERT INTO system (id, constellation_id, name, security_status, system_class, wh_effect_id) VALUES
        (30000142, 20000020, 'Jita', 0.9, NULL, NULL),
        (30000144, 20000020, 'Perimeter', 0.9, NULL, NULL),
        (31000001, 21000001, 'J123456', NULL, 3, 1),
        (31000002, 21000002, 'J234567', NULL, 5, 2),
        (31000003, 21000001, 'J345678', NULL, 3, NULL),
        (-1, NULL, 'Unidentified', NULL, 0, NULL),
        (-4, NULL, 'Unidentified', NULL, 3, NULL),
        (-7, NULL, 'Unidentified', NULL, 5, NULL)
        ON CONFLICT (id) DO NOTHING
        """
    )

    # 6. Insert system statics
    await session.execute(
        """
        INSERT INTO system_static (system_id, wormhole_id) VALUES
        (31000001, 2),
        (31000002, 3)
        ON CONFLICT DO NOTHING
        """
    )

    # 7. Insert test corporation and alliance (needed for user/character setup)
    await session.execute(
        """
        INSERT INTO corporation (id, name, ticker, alliance_id) VALUES
        (98000001, 'Test Corporation', 'TEST', 99000001)
        ON CONFLICT (id) DO NOTHING
        """
    )

    await session.execute(
        """
        INSERT INTO alliance (id, name, ticker) VALUES
        (99000001, 'Test Alliance', 'TSTA')
        ON CONFLICT (id) DO NOTHING
        """
    )
