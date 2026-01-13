"""Factories for static EVE data with curated test values.

These factories provide deterministic test data with explicit values
that match the preseed data in fixtures/preseed.py.
"""

from __future__ import annotations

# Known test system IDs (matching preseed data)
JITA_SYSTEM_ID = 30000142
PERIMETER_SYSTEM_ID = 30000144
J123456_SYSTEM_ID = 31000001  # C3 with Black Hole
J234567_SYSTEM_ID = 31000002  # C5 with Magnetar
J345678_SYSTEM_ID = 31000003  # C3 without effect

# Known test wormhole IDs (matching preseed data)
K162_WORMHOLE_ID = 1  # 24hr lifetime - critical for lifecycle tests
C140_WORMHOLE_ID = 2  # Lowsec static
N944_WORMHOLE_ID = 3  # C5 static
H296_WORMHOLE_ID = 4  # 16hr lifetime C5 static

# Primary test user's entities (matching preseed data)
TEST_CORPORATION_ID = 98000001
TEST_ALLIANCE_ID = 99000001
TEST_CHARACTER_ID = 12345678
TEST_CHARACTER_NAME = "Test Pilot"

# Secondary test user's entities - different corp/alliance for permission testing
TEST2_CORPORATION_ID = 98000002
TEST2_ALLIANCE_ID = 99000002
TEST2_CHARACTER_ID = 87654321
TEST2_CHARACTER_NAME = "Other Pilot"

# Third test user - same corp as primary, different alliance (for corp-level permission testing)
TEST3_CORPORATION_ID = 98000001  # Same corp as primary
TEST3_ALLIANCE_ID = 99000001  # Same alliance as primary
TEST3_CHARACTER_ID = 11111111
TEST3_CHARACTER_NAME = "Corp Mate"

# Pre-created map fixtures (UUIDs are deterministic for testing)
# These maps are created by a fixture owner user, not by the test user
FIXTURE_OWNER_USER_ID = "00000000-0000-0000-0000-000000000001"
CORP_SHARED_MAP_ID = "00000000-0000-0000-0000-000000000101"
CORP_SHARED_MAP_NAME = "Corp Shared Map"
ALLIANCE_SHARED_MAP_ID = "00000000-0000-0000-0000-000000000102"
ALLIANCE_SHARED_MAP_NAME = "Alliance Shared Map"
PUBLIC_MAP_ID = "00000000-0000-0000-0000-000000000103"
PUBLIC_MAP_NAME = "Public Wormhole Atlas"
PUBLIC_MAP_DESCRIPTION = "A public map for all explorers"

# Pre-created nodes on shared maps for permission testing
CORP_MAP_NODE_ID = "00000000-0000-0000-0000-000000000201"
ALLIANCE_MAP_NODE_ID = "00000000-0000-0000-0000-000000000202"
