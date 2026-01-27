"""Factories for static EVE data with curated test values.

These factories provide deterministic test data with explicit values
that match the preseed data in fixtures/preseed.py.
"""

from __future__ import annotations

# Known test system IDs (matching preseed data)
# High-sec trade hubs
JITA_SYSTEM_ID = 30000142
PERIMETER_SYSTEM_ID = 30000144
AMARR_SYSTEM_ID = 30002187
DODIXIE_SYSTEM_ID = 30002659
RENS_SYSTEM_ID = 30002510
HEK_SYSTEM_ID = 30002053

# Null-sec systems for route testing
HED_GP_SYSTEM_ID = 30001161  # HED-GP - famous null-sec entry point
PR_8CA_SYSTEM_ID = 30001198  # PR-8CA - nearby null-sec system

# J-space systems
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

# Fourth test user - for character linking tests (same corp/alliance as primary)
TEST4_CHARACTER_ID = 44444444
TEST4_CHARACTER_NAME = "Linked Alt"

# Ship types for testing
CAPSULE_TYPE_ID = 670

# NPC station for location testing (Jita 4-4)
JITA_44_STATION_ID = 60003760
JITA_44_STATION_NAME = "Jita IV - Moon 4 - Caldari Navy Assembly Plant"

# Player structure for location testing
TEST_STRUCTURE_ID = 1000000000001
TEST_STRUCTURE_NAME = "Test Fortizar"
FORTIZAR_TYPE_ID = 35833

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

# Route testing map and nodes (pre-created for route tests)
ROUTE_TEST_MAP_ID = "00000000-0000-0000-0000-000000000104"
ROUTE_TEST_MAP_NAME = "Route Test Map"
# Nodes on the route test map - forms a small wormhole chain
ROUTE_NODE_JITA_ID = "00000000-0000-0000-0000-000000000301"  # K-space entry
ROUTE_NODE_J123456_ID = "00000000-0000-0000-0000-000000000302"  # C3 wormhole
ROUTE_NODE_J345678_ID = "00000000-0000-0000-0000-000000000303"  # Another C3
ROUTE_NODE_HED_GP_ID = "00000000-0000-0000-0000-000000000304"  # Null-sec exit
# Links on the route test map
ROUTE_LINK_JITA_J123456_ID = "00000000-0000-0000-0000-000000000401"
ROUTE_LINK_J123456_J345678_ID = "00000000-0000-0000-0000-000000000402"
ROUTE_LINK_J345678_HED_GP_ID = "00000000-0000-0000-0000-000000000403"
