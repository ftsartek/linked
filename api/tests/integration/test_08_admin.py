"""Admin and ACL integration tests.

These tests verify the instance-level ACL system including:
- Owner/admin role hierarchy
- ACL CRUD operations (character/corporation/alliance)
- Ownership transfer
- Permission enforcement
"""

from __future__ import annotations

from uuid import UUID

import pytest
from httpx import AsyncClient

from tests.factories.static_data import (
    TEST2_ALLIANCE_ID,
    TEST2_CHARACTER_ID,
    TEST2_CHARACTER_NAME,
    TEST2_CORPORATION_ID,
    TEST_CHARACTER_ID,
    TEST_CHARACTER_NAME,
)
from tests.fixtures.esi_mock import create_mock_access_token
from tests.integration.conftest import IntegrationTestState

# Module-level state for admin tests
_admin_user_id: UUID | None = None


async def authenticate_as_second_user(client: AsyncClient) -> dict:
    """Authenticate as the second test user (TEST2_CHARACTER).

    Returns the user info dict from /auth/me.
    """
    # Set up oauth state
    setup_resp = await client.get("/test/auth-setup")
    assert setup_resp.status_code == 200, f"Auth setup failed: {setup_resp.text}"
    oauth_state = setup_resp.json()["state"]

    # Create mock auth code for second character
    mock_code = create_mock_access_token(TEST2_CHARACTER_ID, TEST2_CHARACTER_NAME)

    # Hit callback
    response = await client.get(
        "/auth/callback",
        params={"code": mock_code, "state": oauth_state},
        follow_redirects=False,
    )
    assert response.status_code == 302, f"Auth callback failed: {response.text}"

    # Get user info
    me_resp = await client.get("/auth/me")
    assert me_resp.status_code == 200, f"Get user info failed: {me_resp.text}"
    return me_resp.json()


# ============================================================================
# Instance Initialization & Owner
# ============================================================================


@pytest.mark.order(800)
async def test_ensure_authenticated(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Ensure the primary test client is authenticated.

    If running admin tests in isolation, this will authenticate.
    If running as part of full suite, test_state is already populated.
    """
    if test_state.user_id is not None:
        # Already authenticated from earlier tests
        return

    # Authenticate via callback (same as test_00_authentication)
    from tests.integration.conftest import authenticate_via_callback

    await authenticate_via_callback(test_client, test_state)
    assert test_state.user_id is not None


@pytest.mark.order(801)
async def test_first_user_becomes_owner(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Verify the first authenticated user is the owner."""
    # Check instance status - owner should be able to access
    response = await test_client.get("/admin/instance")
    assert response.status_code == 200, f"Owner should access admin: {response.text}"

    data = response.json()
    assert data["owner_id"] == str(test_state.user_id)


@pytest.mark.order(802)
async def test_owner_can_get_instance_status(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """GET /admin/instance returns correct owner info."""
    response = await test_client.get("/admin/instance")
    assert response.status_code == 200

    data = response.json()
    assert data["owner_id"] == str(test_state.user_id)
    assert "is_open" in data
    assert "character_acl_count" in data
    assert "corporation_acl_count" in data
    assert "alliance_acl_count" in data
    assert "admin_count" in data


@pytest.mark.order(803)
async def test_instance_starts_closed(
    test_client: AsyncClient,
) -> None:
    """Verify is_open is False initially."""
    response = await test_client.get("/admin/instance")
    assert response.status_code == 200

    data = response.json()
    assert data["is_open"] is False


# ============================================================================
# ACL Management (before admin tests so we can add corp ACL for second user)
# ============================================================================


@pytest.mark.order(805)
async def test_owner_can_add_corporation_acl(
    test_client: AsyncClient,
) -> None:
    """POST /admin/acl/corporations succeeds."""
    # Add the second user's corporation to ACL so they can sign up
    response = await test_client.post(
        "/admin/acl/corporations",
        json={
            "corporation_id": TEST2_CORPORATION_ID,
            "corporation_name": "Test Corp 2",
            "corporation_ticker": "TST2",
        },
    )
    assert response.status_code == 204, f"Failed to add corp ACL: {response.text}"


@pytest.mark.order(806)
async def test_corporation_acl_in_list(
    test_client: AsyncClient,
) -> None:
    """GET /admin/acl/corporations includes entry."""
    response = await test_client.get("/admin/acl/corporations")
    assert response.status_code == 200

    data = response.json()
    corp_ids = [e["corporation_id"] for e in data["entries"]]
    assert TEST2_CORPORATION_ID in corp_ids


# ============================================================================
# Admin Management (Owner-only)
# ============================================================================


@pytest.mark.order(810)
async def test_owner_can_add_admin(
    test_client: AsyncClient,
    second_test_client: AsyncClient,
) -> None:
    """POST /admin/admins with second user succeeds."""
    global _admin_user_id  # noqa: PLW0603

    # First, authenticate the second user so they exist
    user_info = await authenticate_as_second_user(second_test_client)
    _admin_user_id = UUID(user_info["id"])

    # Owner adds them as admin
    response = await test_client.post(
        "/admin/admins",
        json={"user_id": str(_admin_user_id)},
    )
    assert response.status_code == 204, f"Failed to add admin: {response.text}"


@pytest.mark.order(811)
async def test_admin_appears_in_list(
    test_client: AsyncClient,
) -> None:
    """GET /admin/admins includes the new admin."""
    response = await test_client.get("/admin/admins")
    assert response.status_code == 200

    data = response.json()
    admin_ids = [a["user_id"] for a in data["admins"]]
    assert str(_admin_user_id) in admin_ids


@pytest.mark.order(812)
async def test_admin_can_get_instance_status(
    second_test_client: AsyncClient,
) -> None:
    """Admin can access GET /admin/instance."""
    response = await second_test_client.get("/admin/instance")
    assert response.status_code == 200


@pytest.mark.order(813)
async def test_admin_cannot_add_admin(
    second_test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Admin POSTing to /admin/admins returns 403."""
    # Session should persist from test_owner_can_add_admin where we authenticated
    # Try to add the owner as admin (silly, but tests permission)
    response = await second_test_client.post(
        "/admin/admins",
        json={"user_id": str(test_state.user_id)},
    )
    assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"


@pytest.mark.order(814)
async def test_admin_cannot_remove_admin(
    second_test_client: AsyncClient,
) -> None:
    """Admin DELETEing /admin/admins/{id} returns 403."""
    # Try to remove themselves
    response = await second_test_client.delete(f"/admin/admins/{_admin_user_id}")
    assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"


@pytest.mark.order(815)
async def test_admin_can_manage_acl(
    second_test_client: AsyncClient,
) -> None:
    """Admin can add/remove ACL entries."""
    # Add a character ACL
    response = await second_test_client.post(
        "/admin/acl/characters",
        json={"character_id": TEST_CHARACTER_ID, "character_name": TEST_CHARACTER_NAME},
    )
    assert response.status_code == 204, f"Admin should be able to add ACL: {response.text}"

    # Verify it's there
    response = await second_test_client.get("/admin/acl/characters")
    assert response.status_code == 200
    data = response.json()
    char_ids = [e["character_id"] for e in data["entries"]]
    assert TEST_CHARACTER_ID in char_ids

    # Remove it
    response = await second_test_client.delete(f"/admin/acl/characters/{TEST_CHARACTER_ID}")
    assert response.status_code == 204


@pytest.mark.order(816)
async def test_owner_can_remove_admin(
    test_client: AsyncClient,
) -> None:
    """DELETE /admin/admins/{id} succeeds."""
    response = await test_client.delete(f"/admin/admins/{_admin_user_id}")
    assert response.status_code == 204

    # Verify they're gone
    response = await test_client.get("/admin/admins")
    assert response.status_code == 200
    data = response.json()
    admin_ids = [a["user_id"] for a in data["admins"]]
    assert str(_admin_user_id) not in admin_ids


@pytest.mark.order(817)
async def test_removed_admin_loses_access(
    second_test_client: AsyncClient,
) -> None:
    """Removed admin can no longer access admin endpoints."""
    # Second user is still authenticated from earlier tests
    # but their admin status was just removed in test_owner_can_remove_admin
    response = await second_test_client.get("/admin/instance")
    assert response.status_code == 403


# ============================================================================
# ACL Management (continued)
# ============================================================================


@pytest.mark.order(820)
async def test_owner_can_add_character_acl(
    test_client: AsyncClient,
) -> None:
    """POST /admin/acl/characters succeeds."""
    response = await test_client.post(
        "/admin/acl/characters",
        json={"character_id": TEST2_CHARACTER_ID, "character_name": TEST2_CHARACTER_NAME},
    )
    assert response.status_code == 204


@pytest.mark.order(821)
async def test_character_acl_in_list(
    test_client: AsyncClient,
) -> None:
    """GET /admin/acl/characters includes entry."""
    response = await test_client.get("/admin/acl/characters")
    assert response.status_code == 200

    data = response.json()
    char_ids = [e["character_id"] for e in data["entries"]]
    assert TEST2_CHARACTER_ID in char_ids


@pytest.mark.order(822)
async def test_owner_can_remove_character_acl(
    test_client: AsyncClient,
) -> None:
    """DELETE /admin/acl/characters/{id} succeeds."""
    response = await test_client.delete(f"/admin/acl/characters/{TEST2_CHARACTER_ID}")
    assert response.status_code == 204

    # Verify it's gone
    response = await test_client.get("/admin/acl/characters")
    assert response.status_code == 200
    data = response.json()
    char_ids = [e["character_id"] for e in data["entries"]]
    assert TEST2_CHARACTER_ID not in char_ids


@pytest.mark.order(825)
async def test_owner_can_remove_corporation_acl(
    test_client: AsyncClient,
) -> None:
    """DELETE /admin/acl/corporations/{id} succeeds."""
    response = await test_client.delete(f"/admin/acl/corporations/{TEST2_CORPORATION_ID}")
    assert response.status_code == 204

    # Verify it's gone
    response = await test_client.get("/admin/acl/corporations")
    assert response.status_code == 200
    data = response.json()
    corp_ids = [e["corporation_id"] for e in data["entries"]]
    assert TEST2_CORPORATION_ID not in corp_ids


@pytest.mark.order(826)
async def test_owner_can_add_alliance_acl(
    test_client: AsyncClient,
) -> None:
    """POST /admin/acl/alliances succeeds."""
    response = await test_client.post(
        "/admin/acl/alliances",
        json={
            "alliance_id": TEST2_ALLIANCE_ID,
            "alliance_name": "Test Alliance 2",
            "alliance_ticker": "TA2",
        },
    )
    assert response.status_code == 204


@pytest.mark.order(827)
async def test_alliance_acl_in_list(
    test_client: AsyncClient,
) -> None:
    """GET /admin/acl/alliances includes entry."""
    response = await test_client.get("/admin/acl/alliances")
    assert response.status_code == 200

    data = response.json()
    alliance_ids = [e["alliance_id"] for e in data["entries"]]
    assert TEST2_ALLIANCE_ID in alliance_ids


@pytest.mark.order(828)
async def test_owner_can_remove_alliance_acl(
    test_client: AsyncClient,
) -> None:
    """DELETE /admin/acl/alliances/{id} succeeds."""
    response = await test_client.delete(f"/admin/acl/alliances/{TEST2_ALLIANCE_ID}")
    assert response.status_code == 204

    # Verify it's gone
    response = await test_client.get("/admin/acl/alliances")
    assert response.status_code == 200
    data = response.json()
    alliance_ids = [e["alliance_id"] for e in data["entries"]]
    assert TEST2_ALLIANCE_ID not in alliance_ids


# ============================================================================
# Instance Settings
# ============================================================================


@pytest.mark.order(830)
async def test_owner_can_update_is_open(
    test_client: AsyncClient,
) -> None:
    """PATCH /admin/instance with is_open=true succeeds."""
    response = await test_client.patch(
        "/admin/instance",
        json={"is_open": True},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["is_open"] is True


@pytest.mark.order(831)
async def test_instance_is_now_open(
    test_client: AsyncClient,
) -> None:
    """Verify is_open is True after update."""
    response = await test_client.get("/admin/instance")
    assert response.status_code == 200

    data = response.json()
    assert data["is_open"] is True

    # Set it back to closed for subsequent tests
    await test_client.patch("/admin/instance", json={"is_open": False})


# ============================================================================
# Ownership Transfer
# ============================================================================


@pytest.mark.order(840)
async def test_re_add_admin_for_transfer_tests(
    test_client: AsyncClient,
    second_test_client: AsyncClient,
) -> None:
    """Re-add the second user as admin for transfer tests."""
    global _admin_user_id  # noqa: PLW0603

    # Add corp ACL first so second user can access
    await test_client.post(
        "/admin/acl/corporations",
        json={
            "corporation_id": TEST2_CORPORATION_ID,
            "corporation_name": "Test Corp 2",
            "corporation_ticker": "TST2",
        },
    )

    # Re-authenticate second user
    user_info = await authenticate_as_second_user(second_test_client)
    _admin_user_id = UUID(user_info["id"])

    # Add as admin
    response = await test_client.post(
        "/admin/admins",
        json={"user_id": str(_admin_user_id)},
    )
    assert response.status_code == 204


@pytest.mark.order(841)
async def test_admin_cannot_transfer_ownership(
    second_test_client: AsyncClient,
) -> None:
    """Admin POSTing to /admin/instance/transfer returns 403."""
    # Second user is already authenticated from test_re_add_admin_for_transfer_tests
    response = await second_test_client.post(
        "/admin/instance/transfer",
        json={"new_owner_id": str(_admin_user_id)},
    )
    assert response.status_code == 403


@pytest.mark.order(842)
async def test_owner_cannot_transfer_to_self(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Transfer to self returns 400."""
    response = await test_client.post(
        "/admin/instance/transfer",
        json={"new_owner_id": str(test_state.user_id)},
    )
    assert response.status_code == 400


@pytest.mark.order(843)
async def test_owner_can_transfer_ownership(
    test_client: AsyncClient,
) -> None:
    """POST /admin/instance/transfer succeeds."""
    response = await test_client.post(
        "/admin/instance/transfer",
        json={"new_owner_id": str(_admin_user_id)},
    )
    # POST returns 201 Created
    assert response.status_code == 201

    data = response.json()
    assert data["owner_id"] == str(_admin_user_id)


@pytest.mark.order(844)
async def test_new_owner_has_access(
    second_test_client: AsyncClient,
) -> None:
    """New owner can GET /admin/instance."""
    response = await second_test_client.get("/admin/instance")
    assert response.status_code == 200

    data = response.json()
    assert data["owner_id"] == str(_admin_user_id)


@pytest.mark.order(845)
async def test_old_owner_is_no_longer_owner(
    test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Old owner cannot POST to /admin/instance/transfer."""
    response = await test_client.post(
        "/admin/instance/transfer",
        json={"new_owner_id": str(test_state.user_id)},
    )
    # Old owner is no longer owner or admin, so should be 403
    # (but they may still be authenticated, so not 401)
    assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"


@pytest.mark.order(846)
async def test_transfer_back_to_original(
    second_test_client: AsyncClient,
    test_state: IntegrationTestState,
) -> None:
    """Transfer ownership back for subsequent tests."""
    # Second user should still be authenticated from earlier tests
    # (test_new_owner_has_access just verified they have access)
    response = await second_test_client.post(
        "/admin/instance/transfer",
        json={"new_owner_id": str(test_state.user_id)},
    )
    # POST returns 201 Created
    assert response.status_code == 201, f"Transfer failed: {response.text}"

    data = response.json()
    assert data["owner_id"] == str(test_state.user_id)


# ============================================================================
# Permission Denied Cases
# ============================================================================


@pytest.mark.order(850)
async def test_unauthenticated_cannot_access_admin(
    unauthenticated_client: AsyncClient,
) -> None:
    """GET /admin/instance without auth returns 401."""
    response = await unauthenticated_client.get("/admin/instance")
    assert response.status_code == 401


@pytest.mark.order(851)
async def test_regular_user_cannot_access_admin(
    second_test_client: AsyncClient,
    test_client: AsyncClient,
) -> None:
    """Non-admin user gets 403 on admin endpoints."""
    # Remove second user from admin list first (if they're still admin)
    # Note: After transfer tests, ownership may have changed, so this might fail
    # Accept any status - we just want to ensure they're not admin
    await test_client.delete(f"/admin/admins/{_admin_user_id}")

    # Second user should be denied (403 Forbidden, not 401 Unauthorized)
    # They are still authenticated from earlier, but not privileged
    response = await second_test_client.get("/admin/instance")
    assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"


# ============================================================================
# Cleanup - restore state for other tests
# ============================================================================


@pytest.mark.order(899)
async def test_cleanup_acl_state(
    test_client: AsyncClient,
) -> None:
    """Clean up ACL state to not interfere with other tests."""
    # Remove corp ACL we added
    await test_client.delete(f"/admin/acl/corporations/{TEST2_CORPORATION_ID}")

    # Set instance to open so other tests can run
    # (since ACL is enforced on authenticated routes)
    await test_client.patch("/admin/instance", json={"is_open": True})
