"""Test 07: Link lifecycle management.

Tests the link lifetime lifecycle service with deterministic time control.
Uses K162 wormhole (24hr lifetime) and explicit current_time parameter.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID

import pytest

if TYPE_CHECKING:
    from litestar.testing import AsyncTestClient
    from sqlspec.adapters.asyncpg.driver import AsyncpgDriver

    from tests.integration.conftest import TestState

from services.lifecycle import update_link_lifetimes
from tests.factories.static_data import J234567_SYSTEM_ID, K162_WORMHOLE_ID
from tests.integration.conftest import set_auth
from utils.enums import LifetimeStatus


class TestLifecycle:
    """Test link lifetime lifecycle with fixed timestamps."""

    @pytest.mark.order(24)
    async def test_create_lifecycle_test_node(
        self,
        test_client: AsyncTestClient,
        test_state: TestState,
    ) -> None:
        """Create a third node for lifecycle testing."""
        await set_auth(test_client, test_state)

        response = await test_client.post(
            f"/maps/{test_state.map_id}/nodes",
            json={
                "system_id": J234567_SYSTEM_ID,
                "pos_x": 500.0,
                "pos_y": 100.0,
            },
        )

        assert response.status_code == 201
        node_id = UUID(response.json()["node_id"])
        test_state.node_ids.append(node_id)

    @pytest.mark.order(25)
    async def test_create_lifecycle_test_link(
        self,
        test_client: AsyncTestClient,
        test_state: TestState,
    ) -> None:
        """Create a link specifically for lifecycle testing with K162."""
        await set_auth(test_client, test_state)

        # Link from J123456 to J234567
        source_node_id = test_state.node_ids[1]  # J123456
        target_node_id = test_state.node_ids[2]  # J234567

        response = await test_client.post(
            f"/maps/{test_state.map_id}/links",
            json={
                "source_node_id": str(source_node_id),
                "target_node_id": str(target_node_id),
                "wormhole_id": K162_WORMHOLE_ID,
            },
        )

        assert response.status_code == 201
        link_id = UUID(response.json()["link_id"])
        test_state.lifecycle_link_id = link_id
        test_state.link_ids.append(link_id)

    @pytest.mark.order(26)
    async def test_lifecycle_stable_to_aging(
        self,
        db_session: AsyncpgDriver,
        test_state: TestState,
    ) -> None:
        """Test transition from STABLE to AGING after time passes.

        K162 has 24hr lifetime. If we set the status timestamp to 20hrs ago,
        there are 4hrs remaining which should trigger AGING status.
        """
        base_time = datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC)
        status_time = base_time - timedelta(hours=20)  # 4hrs remaining

        # Set link to STABLE with timestamp 20hrs ago
        await db_session.execute(
            "UPDATE link SET lifetime_status = $1, date_lifetime_updated = $2 WHERE id = $3",
            [LifetimeStatus.STABLE.value, status_time, test_state.lifecycle_link_id],
        )

        # Run lifecycle update with explicit current_time
        result = await update_link_lifetimes(
            db_session,
            current_time=base_time,
            dry_run=False,
            event_publisher=None,
        )

        assert result.updated_count >= 1
        assert test_state.lifecycle_link_id in result.updated_ids

        # Verify the status was updated in the database
        row = await db_session.select_one(
            "SELECT lifetime_status FROM link WHERE id = $1",
            [test_state.lifecycle_link_id],
        )
        assert row["lifetime_status"] == LifetimeStatus.AGING.value

    @pytest.mark.order(27)
    async def test_lifecycle_aging_to_critical(
        self,
        db_session: AsyncpgDriver,
        test_state: TestState,
    ) -> None:
        """Test transition from AGING to CRITICAL.

        With AGING status and < 4hrs remaining, should transition to CRITICAL.
        """
        base_time = datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC)
        # Set to AGING with timestamp such that ~2hrs remaining
        status_time = base_time - timedelta(hours=22)

        await db_session.execute(
            "UPDATE link SET lifetime_status = $1, date_lifetime_updated = $2 WHERE id = $3",
            [LifetimeStatus.AGING.value, status_time, test_state.lifecycle_link_id],
        )

        result = await update_link_lifetimes(
            db_session,
            current_time=base_time,
            dry_run=False,
            event_publisher=None,
        )

        assert result.updated_count >= 1

        row = await db_session.select_one(
            "SELECT lifetime_status FROM link WHERE id = $1",
            [test_state.lifecycle_link_id],
        )
        assert row["lifetime_status"] == LifetimeStatus.CRITICAL.value

    @pytest.mark.order(28)
    async def test_lifecycle_critical_to_eol(
        self,
        db_session: AsyncpgDriver,
        test_state: TestState,
    ) -> None:
        """Test transition from CRITICAL to EOL.

        CRITICAL status means < 4hrs remaining when marked.
        After 3.5hrs elapsed, remaining = 4 - 3.5 = 0.5hrs < 1hr → EOL.
        """
        base_time = datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC)
        # Set CRITICAL 3.5hrs ago → 0.5hrs remaining → should transition to EOL
        status_time = base_time - timedelta(hours=3, minutes=30)

        await db_session.execute(
            "UPDATE link SET lifetime_status = $1, date_lifetime_updated = $2, date_deleted = NULL WHERE id = $3",
            [LifetimeStatus.CRITICAL.value, status_time, test_state.lifecycle_link_id],
        )

        result = await update_link_lifetimes(
            db_session,
            current_time=base_time,
            dry_run=False,
            event_publisher=None,
        )

        assert result.updated_count >= 1

        row = await db_session.select_one(
            "SELECT lifetime_status, date_deleted FROM link WHERE id = $1",
            [test_state.lifecycle_link_id],
        )

        # Should transition to EOL (not deleted - that happens after EOL grace period)
        assert row["date_deleted"] is None, "Link should not be deleted yet"
        assert row["lifetime_status"] == LifetimeStatus.EOL.value

    @pytest.mark.order(29)
    async def test_lifecycle_eol_deletion(
        self,
        db_session: AsyncpgDriver,
        test_state: TestState,
    ) -> None:
        """Test that EOL links get soft-deleted after expiration.

        EOL has a grace period (~1hr), after which the link should be soft-deleted.
        """
        # First, ensure the link exists and is in EOL state
        await db_session.execute(
            "UPDATE link SET lifetime_status = $1, date_deleted = NULL WHERE id = $2",
            [LifetimeStatus.EOL.value, test_state.lifecycle_link_id],
        )

        base_time = datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC)
        # Set to EOL with timestamp 2hrs ago (well past expiry)
        status_time = base_time - timedelta(hours=2)

        await db_session.execute(
            "UPDATE link SET date_lifetime_updated = $1 WHERE id = $2",
            [status_time, test_state.lifecycle_link_id],
        )

        result = await update_link_lifetimes(
            db_session,
            current_time=base_time,
            dry_run=False,
            event_publisher=None,
        )

        assert result.deleted_count >= 1
        assert test_state.lifecycle_link_id in result.deleted_ids

        # Verify the link was soft-deleted
        row = await db_session.select_one(
            "SELECT date_deleted FROM link WHERE id = $1",
            [test_state.lifecycle_link_id],
        )
        assert row["date_deleted"] is not None

    @pytest.mark.order(30)
    async def test_lifecycle_dry_run(
        self,
        db_session: AsyncpgDriver,
        test_state: TestState,
    ) -> None:
        """Test that dry_run mode calculates changes without applying them."""
        # Create a new link for this test
        link_id = test_state.link_ids[0]  # Use the first link
        base_time = datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC)
        status_time = base_time - timedelta(hours=20)

        # Get current status
        before = await db_session.select_one(
            "SELECT lifetime_status FROM link WHERE id = $1 AND date_deleted IS NULL",
            [link_id],
        )

        if before is None:
            pytest.skip("First link was deleted, skipping dry run test")

        # Set to STABLE with old timestamp
        await db_session.execute(
            "UPDATE link SET lifetime_status = $1, date_lifetime_updated = $2 WHERE id = $3",
            [LifetimeStatus.STABLE.value, status_time, link_id],
        )

        # Run with dry_run=True
        result = await update_link_lifetimes(
            db_session,
            current_time=base_time,
            dry_run=True,
            event_publisher=None,
        )

        # Should report updates but not actually apply them
        assert result.updated_count >= 1

        # Verify status was NOT changed
        after = await db_session.select_one(
            "SELECT lifetime_status FROM link WHERE id = $1",
            [link_id],
        )
        assert after["lifetime_status"] == LifetimeStatus.STABLE.value
