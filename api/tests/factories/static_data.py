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

# Known test entity IDs (matching preseed data)
TEST_CORPORATION_ID = 98000001
TEST_ALLIANCE_ID = 99000001
TEST_CHARACTER_ID = 12345678
TEST_CHARACTER_NAME = "Test Pilot"
