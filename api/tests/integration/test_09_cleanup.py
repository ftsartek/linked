"""Test 09: Cleanup service.

Tests the hard-deletion cleanup service that removes soft-deleted records
after the retention period has passed.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

if TYPE_CHECKING:
    from sqlspec.adapters.asyncpg.driver import AsyncpgDriver

    from tests.integration.conftest import TestState

from services.cleanup import cleanup_all, cleanup_maps


class TestCleanup:
    """Test cleanup service for hard-deleting old soft-deleted records."""

    @pytest.mark.order(36)
    async def test_cleanup_old_soft_deleted_records(
        self,
        db_session: AsyncpgDriver,
        test_state: TestState,
    ) -> None:
        """Test that old soft-deleted records are hard-deleted."""
        current_time = datetime.now(UTC)
        old_time = current_time - timedelta(hours=48)

        # Update only soft-deleted records from this test's map to have an old date_deleted
        # This avoids affecting data from other tests if run in parallel
        await db_session.execute(
            "UPDATE link SET date_deleted = $1 WHERE map_id = $2 AND date_deleted IS NOT NULL",
            [old_time, test_state.map_id],
        )
        await db_session.execute(
            "UPDATE node SET date_deleted = $1 WHERE map_id = $2 AND date_deleted IS NOT NULL",
            [old_time, test_state.map_id],
        )
        await db_session.execute(
            "UPDATE map SET date_deleted = $1 WHERE id = $2 AND date_deleted IS NOT NULL",
            [old_time, test_state.map_id],
        )

        # Run cleanup with 24hr retention
        result = await cleanup_all(
            db_session,
            retention_hours=24,
            dry_run=False,
            current_time=current_time,
        )

        # Verify at least some records were deleted (we set up soft-deleted data above)
        assert result.total >= 1, "Expected at least one record to be cleaned up"

        # Verify the test map's old records are gone from database
        map_after = await db_session.select_one(
            "SELECT id FROM map WHERE id = $1",
            [test_state.map_id],
        )
        assert map_after is None, "Test map should have been hard-deleted"

    @pytest.mark.order(37)
    async def test_cleanup_respects_retention_period(
        self,
        db_session: AsyncpgDriver,
        test_state: TestState,
    ) -> None:
        """Test that recent soft-deleted records are NOT deleted."""
        current_time = datetime.now(UTC)
        recent_time = current_time - timedelta(hours=1)  # Just 1 hour ago

        # Create a new map and immediately soft-delete it
        new_map_id = uuid4()
        await db_session.execute(
            "INSERT INTO map (id, owner_id, name, date_deleted) VALUES ($1, $2, $3, $4)",
            [new_map_id, test_state.user_id, "Cleanup Test Map", recent_time],
        )

        # Run cleanup with 24hr retention
        await cleanup_all(
            db_session,
            retention_hours=24,
            dry_run=False,
            current_time=current_time,
        )

        # The recently deleted map should NOT be cleaned up
        row = await db_session.select_one(
            "SELECT id FROM map WHERE id = $1",
            [new_map_id],
        )
        assert row is not None, "Recently soft-deleted map was incorrectly hard-deleted"

        # Clean up the test map manually for next tests
        await db_session.execute(
            "DELETE FROM map WHERE id = $1",
            [new_map_id],
        )

    @pytest.mark.order(38)
    async def test_cleanup_dry_run(
        self,
        db_session: AsyncpgDriver,
        test_state: TestState,
    ) -> None:
        """Test that dry_run mode counts but doesn't delete records."""
        current_time = datetime.now(UTC)
        old_time = current_time - timedelta(hours=48)

        # Create a map to test with
        test_map_id = uuid4()
        await db_session.execute(
            "INSERT INTO map (id, owner_id, name, date_deleted) VALUES ($1, $2, $3, $4)",
            [test_map_id, test_state.user_id, "Dry Run Test Map", old_time],
        )

        # Run cleanup with dry_run=True
        result = await cleanup_all(
            db_session,
            retention_hours=24,
            dry_run=True,
            current_time=current_time,
        )

        # Should report at least 1 map would be deleted
        assert result.maps_deleted >= 1

        # Verify the map still exists (dry run didn't delete it)
        row = await db_session.select_one(
            "SELECT id FROM map WHERE id = $1",
            [test_map_id],
        )
        assert row is not None, "Dry run incorrectly deleted the map"

        # Now actually delete it
        await db_session.execute(
            "DELETE FROM map WHERE id = $1",
            [test_map_id],
        )

    @pytest.mark.order(39)
    async def test_cleanup_individual_entity_types(
        self,
        db_session: AsyncpgDriver,
        test_state: TestState,
    ) -> None:
        """Test cleaning up individual entity types."""
        current_time = datetime.now(UTC)
        old_time = current_time - timedelta(hours=48)

        # Create a test map
        test_map_id = uuid4()
        await db_session.execute(
            "INSERT INTO map (id, owner_id, name, date_deleted) VALUES ($1, $2, $3, $4)",
            [test_map_id, test_state.user_id, "Individual Cleanup Test", old_time],
        )

        # Test cleanup_maps specifically
        maps_deleted = await cleanup_maps(
            db_session,
            retention_hours=24,
            dry_run=False,
            current_time=current_time,
        )

        assert maps_deleted >= 1

        # Verify it's gone
        rows = await db_session.select(
            "SELECT id FROM map WHERE id = $1",
            [test_map_id],
        )
        assert len(rows) == 0, "Map was not deleted"

    @pytest.mark.order(40)
    async def test_cleanup_order_respects_fk_constraints(
        self,
        db_session: AsyncpgDriver,
        test_state: TestState,
    ) -> None:
        """Test that cleanup_all deletes in FK-safe order."""
        current_time = datetime.now(UTC)
        old_time = current_time - timedelta(hours=48)

        # Create a map with a node and link
        test_map_id = uuid4()
        test_node_id = uuid4()

        await db_session.execute(
            "INSERT INTO map (id, owner_id, name, date_deleted) VALUES ($1, $2, $3, $4)",
            [test_map_id, test_state.user_id, "FK Test Map", old_time],
        )

        await db_session.execute(
            "INSERT INTO node (id, map_id, system_id, pos_x, pos_y, date_deleted) VALUES ($1, $2, $3, $4, $5, $6)",
            [test_node_id, test_map_id, 30000142, 0.0, 0.0, old_time],
        )

        # cleanup_all should handle the FK order: links -> nodes -> maps
        result = await cleanup_all(
            db_session,
            retention_hours=24,
            dry_run=False,
            current_time=current_time,
        )

        # Both should be deleted without FK violations
        assert result.nodes_deleted >= 1
        assert result.maps_deleted >= 1

        # Verify they're gone
        node_rows = await db_session.select(
            "SELECT id FROM node WHERE id = $1",
            [test_node_id],
        )
        assert len(node_rows) == 0, "Node was not deleted"

        map_rows = await db_session.select(
            "SELECT id FROM map WHERE id = $1",
            [test_map_id],
        )
        assert len(map_rows) == 0, "Map was not deleted"
