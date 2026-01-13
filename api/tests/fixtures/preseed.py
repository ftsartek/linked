"""Curated preseed data for tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

from tests.factories.static_data import (
    ALLIANCE_MAP_NODE_ID,
    ALLIANCE_SHARED_MAP_ID,
    ALLIANCE_SHARED_MAP_NAME,
    CORP_MAP_NODE_ID,
    CORP_SHARED_MAP_ID,
    CORP_SHARED_MAP_NAME,
    FIXTURE_OWNER_USER_ID,
    J123456_SYSTEM_ID,
    JITA_SYSTEM_ID,
    PUBLIC_MAP_DESCRIPTION,
    PUBLIC_MAP_ID,
    PUBLIC_MAP_NAME,
    TEST2_ALLIANCE_ID,
    TEST2_CHARACTER_ID,
    TEST2_CHARACTER_NAME,
    TEST2_CORPORATION_ID,
    TEST_ALLIANCE_ID,
    TEST_CORPORATION_ID,
)

if TYPE_CHECKING:
    from sqlspec.adapters.asyncpg.driver import AsyncpgDriver


async def preseed_test_data(session: AsyncpgDriver) -> None:
    """Insert curated test data into the database.

    This creates a minimal but realistic dataset for testing:
    - Wormhole types (K162 with 24hr lifetime is critical for lifecycle tests)
    - Regions, constellations, and systems including both k-space and w-space
    - Effects for wormhole systems
    - System statics
    - Corporations and alliances for permission testing
    - Pre-created maps with various sharing configurations
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

    # 7. Insert alliances (must be before corporations due to FK)
    await session.execute(
        f"""
        INSERT INTO alliance (id, name, ticker) VALUES
        ({TEST_ALLIANCE_ID}, 'Test Alliance', 'TSTA'),
        ({TEST2_ALLIANCE_ID}, 'Other Alliance', 'OTHA')
        ON CONFLICT (id) DO NOTHING
        """
    )

    # 8. Insert test corporations
    await session.execute(
        f"""
        INSERT INTO corporation (id, name, ticker, alliance_id) VALUES
        ({TEST_CORPORATION_ID}, 'Test Corporation', 'TEST', {TEST_ALLIANCE_ID}),
        ({TEST2_CORPORATION_ID}, 'Other Corporation', 'OTHR', {TEST2_ALLIANCE_ID})
        ON CONFLICT (id) DO NOTHING
        """
    )

    # 9. Insert fixture owner user (for pre-created maps)
    await session.execute(
        f"""
        INSERT INTO "user" (id) VALUES
        ('{FIXTURE_OWNER_USER_ID}')
        ON CONFLICT (id) DO NOTHING
        """
    )

    # 10. Insert test characters (for character-level access testing)
    # Only preseed TEST2_CHARACTER - the primary TEST_CHARACTER will be created
    # during auth callback, and we don't want to interfere with user creation.
    # These use FIXTURE_OWNER_USER_ID as placeholder since user_id is required.
    await session.execute(
        f"""
        INSERT INTO character (id, user_id, corporation_id, name) VALUES
        ({TEST2_CHARACTER_ID}, '{FIXTURE_OWNER_USER_ID}', {TEST2_CORPORATION_ID}, '{TEST2_CHARACTER_NAME}')
        ON CONFLICT (id) DO NOTHING
        """
    )

    # 11. Insert pre-created maps with various sharing configurations
    # These maps are owned by fixture_owner, not by the test user
    await session.execute(
        f"""
        INSERT INTO map (id, owner_id, name, description, is_public, public_read_only) VALUES
        ('{CORP_SHARED_MAP_ID}', '{FIXTURE_OWNER_USER_ID}', '{CORP_SHARED_MAP_NAME}',
         'A map shared with Test Corporation', false, true),
        ('{ALLIANCE_SHARED_MAP_ID}', '{FIXTURE_OWNER_USER_ID}', '{ALLIANCE_SHARED_MAP_NAME}',
         'A map shared with Test Alliance', false, true),
        ('{PUBLIC_MAP_ID}', '{FIXTURE_OWNER_USER_ID}', '{PUBLIC_MAP_NAME}',
         '{PUBLIC_MAP_DESCRIPTION}', true, true)
        ON CONFLICT (id) DO NOTHING
        """
    )

    # 12. Set up map sharing permissions
    # Corp shared map - shared with TEST_CORPORATION_ID (read-write)
    await session.execute(
        f"""
        INSERT INTO map_corporation (map_id, corporation_id, read_only) VALUES
        ('{CORP_SHARED_MAP_ID}', {TEST_CORPORATION_ID}, false)
        ON CONFLICT DO NOTHING
        """
    )

    # Alliance shared map - shared with TEST_ALLIANCE_ID (read-only)
    await session.execute(
        f"""
        INSERT INTO map_alliance (map_id, alliance_id, read_only) VALUES
        ('{ALLIANCE_SHARED_MAP_ID}', {TEST_ALLIANCE_ID}, true)
        ON CONFLICT DO NOTHING
        """
    )

    # 13. Insert nodes on shared maps for permission testing
    # Node on corp shared map (for testing non-owner lock operations)
    await session.execute(
        f"""
        INSERT INTO node (id, map_id, system_id, pos_x, pos_y) VALUES
        ('{CORP_MAP_NODE_ID}', '{CORP_SHARED_MAP_ID}', {JITA_SYSTEM_ID}, 100.0, 100.0),
        ('{ALLIANCE_MAP_NODE_ID}', '{ALLIANCE_SHARED_MAP_ID}', {J123456_SYSTEM_ID}, 100.0, 100.0)
        ON CONFLICT (id) DO NOTHING
        """
    )
