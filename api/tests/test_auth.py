from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from litestar.testing import TestClient

from routes.auth.service import CharacterInfo, CharacterUserInfo
from tests.conftest import MockCharacterInfo, MockTokenResponse, TEST_USER_UUID, TEST_USER_UUID_2


class TestLogin:
    """Tests for GET /auth/login endpoint."""

    def test_login_redirects_to_eve_sso(
        self, client: TestClient, mock_sso_service: MagicMock
    ) -> None:
        """Login should redirect to EVE SSO authorization URL."""
        response = client.get("/auth/login", follow_redirects=False)

        assert response.status_code == 302
        assert response.headers["location"] == "https://login.eveonline.com/v2/oauth/authorize?mock=true"
        mock_sso_service.get_authorization_url.assert_called_once()

    def test_login_stores_state_in_session(
        self, client: TestClient, mock_sso_service: MagicMock
    ) -> None:
        """Login should store OAuth state in session for CSRF protection."""
        client.get("/auth/login", follow_redirects=False)

        # Verify state was passed to SSO service
        call_args = mock_sso_service.get_authorization_url.call_args
        state = call_args[0][0]  # First positional argument
        assert state is not None
        assert len(state) > 20  # Should be a secure random string


class TestCallback:
    """Tests for GET /auth/callback endpoint."""

    def test_callback_rejects_invalid_state(self, client: TestClient) -> None:
        """Callback should reject requests with invalid state parameter."""
        response = client.get("/auth/callback?code=test&state=invalid")

        assert response.status_code == 401

    def test_callback_creates_new_user_for_unknown_character(
        self,
        client: TestClient,
        mock_sso_service: MagicMock,
        mock_db_session: MagicMock,
    ) -> None:
        """Callback should create new user when character is not in database."""
        # First, do login to set up session state
        client.get("/auth/login", follow_redirects=False)

        # Get the state that was used
        state = mock_sso_service.get_authorization_url.call_args[0][0]

        # Mock: character doesn't exist, user insert returns new user id
        mock_db_session.select_one_or_none = AsyncMock(return_value=None)
        mock_db_session.select_value = AsyncMock(return_value=TEST_USER_UUID)  # new user_id
        mock_db_session.execute = AsyncMock(return_value=MagicMock())

        response = client.get(
            f"/auth/callback?code=test_code&state={state}",
            follow_redirects=False,
        )

        assert response.status_code == 302
        mock_sso_service.exchange_code.assert_called_once_with("test_code")
        mock_sso_service.validate_jwt.assert_called_once()

    def test_callback_logs_in_existing_user(
        self,
        client: TestClient,
        mock_sso_service: MagicMock,
        mock_db_session: MagicMock,
    ) -> None:
        """Callback should log in existing user when character exists."""
        client.get("/auth/login", follow_redirects=False)
        state = mock_sso_service.get_authorization_url.call_args[0][0]

        # Mock: character exists with user_id
        mock_db_session.select_one_or_none = AsyncMock(
            return_value=CharacterUserInfo(
                id=12345678, user_id=TEST_USER_UUID, name="Test Pilot",
                corporation_id=None, alliance_id=None
            )
        )
        mock_db_session.execute = AsyncMock(return_value=MagicMock())

        response = client.get(
            f"/auth/callback?code=test_code&state={state}",
            follow_redirects=False,
        )

        assert response.status_code == 302


class TestLogout:
    """Tests for POST /auth/logout endpoint."""

    def test_logout_clears_session(
        self,
        client: TestClient,
        mock_sso_service: MagicMock,
        mock_db_session: MagicMock,
    ) -> None:
        """Logout should clear the session and return success."""
        # Set up a logged-in session
        client.get("/auth/login", follow_redirects=False)
        state = mock_sso_service.get_authorization_url.call_args[0][0]

        mock_db_session.select_one_or_none = AsyncMock(
            return_value=CharacterUserInfo(
                id=12345678, user_id=TEST_USER_UUID, name="Test Pilot",
                corporation_id=None, alliance_id=None
            )
        )
        mock_db_session.execute = AsyncMock(return_value=MagicMock())

        client.get(f"/auth/callback?code=test&state={state}", follow_redirects=False)

        # Now logout
        response = client.post("/auth/logout")

        assert response.status_code == 201
        assert response.json() == {"success": True}


class TestMe:
    """Tests for GET /auth/me endpoint."""

    def test_me_requires_authentication(self, client: TestClient) -> None:
        """Me endpoint should require authentication."""
        response = client.get("/auth/me")

        assert response.status_code == 401

    def test_me_returns_user_info(
        self,
        client: TestClient,
        mock_sso_service: MagicMock,
        mock_db_session: MagicMock,
    ) -> None:
        """Me endpoint should return user and character info when authenticated."""
        # Log in first
        client.get("/auth/login", follow_redirects=False)
        state = mock_sso_service.get_authorization_url.call_args[0][0]

        # Mock callback: existing character
        mock_db_session.select_one_or_none = AsyncMock(
            return_value=CharacterUserInfo(
                id=12345678, user_id=TEST_USER_UUID, name="Test Pilot",
                corporation_id=98000001, alliance_id=None
            )
        )
        mock_db_session.execute = AsyncMock(return_value=MagicMock())

        client.get(f"/auth/callback?code=test&state={state}", follow_redirects=False)

        # Now mock the /me query - mock select to return CharacterInfo list
        mock_db_session.select = AsyncMock(
            return_value=[
                CharacterInfo(id=12345678, name="Test Pilot", corporation_id=98000001, alliance_id=None),
                CharacterInfo(id=87654321, name="Alt Character", corporation_id=98000002, alliance_id=99000001),
            ]
        )

        response = client.get("/auth/me")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(TEST_USER_UUID)
        assert len(data["characters"]) == 2
        assert data["characters"][0]["name"] == "Test Pilot"
        assert data["characters"][1]["name"] == "Alt Character"


class TestLink:
    """Tests for GET /auth/link endpoint."""

    def test_link_requires_authentication(self, client: TestClient) -> None:
        """Link endpoint should require authentication."""
        response = client.get("/auth/link", follow_redirects=False)

        assert response.status_code == 401

    def test_link_redirects_to_eve_sso(
        self,
        client: TestClient,
        mock_sso_service: MagicMock,
        mock_db_session: MagicMock,
    ) -> None:
        """Link should redirect to EVE SSO when authenticated."""
        # Log in first
        client.get("/auth/login", follow_redirects=False)
        state = mock_sso_service.get_authorization_url.call_args[0][0]

        mock_db_session.select_one_or_none = AsyncMock(
            return_value=CharacterUserInfo(
                id=12345678, user_id=TEST_USER_UUID, name="Test Pilot",
                corporation_id=None, alliance_id=None
            )
        )
        mock_db_session.execute = AsyncMock(return_value=MagicMock())

        client.get(f"/auth/callback?code=test&state={state}", follow_redirects=False)

        # Reset mock to track the link call
        mock_sso_service.get_authorization_url.reset_mock()

        response = client.get("/auth/link", follow_redirects=False)

        assert response.status_code == 302
        mock_sso_service.get_authorization_url.assert_called_once()

    def test_link_callback_adds_character_to_user(
        self,
        client: TestClient,
        mock_sso_service: MagicMock,
        mock_db_session: MagicMock,
    ) -> None:
        """Link callback should add new character to current user."""
        # Log in first
        client.get("/auth/login", follow_redirects=False)
        state = mock_sso_service.get_authorization_url.call_args[0][0]

        mock_db_session.select_one_or_none = AsyncMock(
            return_value=CharacterUserInfo(
                id=12345678, user_id=TEST_USER_UUID, name="Test Pilot",
                corporation_id=None, alliance_id=None
            )
        )
        mock_db_session.execute = AsyncMock(return_value=MagicMock())

        client.get(f"/auth/callback?code=test&state={state}", follow_redirects=False)

        # Now start link flow
        mock_sso_service.get_authorization_url.reset_mock()
        client.get("/auth/link", follow_redirects=False)
        link_state = mock_sso_service.get_authorization_url.call_args[0][0]

        # Mock a different character for linking
        mock_sso_service.validate_jwt.return_value = MockCharacterInfo(
            character_id=87654321,
            character_name="Alt Character",
        )

        # Mock: new character doesn't exist
        mock_db_session.select_one_or_none = AsyncMock(return_value=None)
        mock_db_session.execute = AsyncMock(return_value=MagicMock())

        response = client.get(
            f"/auth/callback?code=link_code&state={link_state}",
            follow_redirects=False,
        )

        assert response.status_code == 302

    def test_link_rejects_character_owned_by_other_user(
        self,
        client: TestClient,
        mock_sso_service: MagicMock,
        mock_db_session: MagicMock,
    ) -> None:
        """Link should reject character already owned by another user."""
        # Log in as user
        client.get("/auth/login", follow_redirects=False)
        state = mock_sso_service.get_authorization_url.call_args[0][0]

        mock_db_session.select_one_or_none = AsyncMock(
            return_value=CharacterUserInfo(
                id=12345678, user_id=TEST_USER_UUID, name="Test Pilot",
                corporation_id=None, alliance_id=None
            )
        )
        mock_db_session.execute = AsyncMock(return_value=MagicMock())

        client.get(f"/auth/callback?code=test&state={state}", follow_redirects=False)

        # Start link flow
        mock_sso_service.get_authorization_url.reset_mock()
        client.get("/auth/link", follow_redirects=False)
        link_state = mock_sso_service.get_authorization_url.call_args[0][0]

        # Mock: character exists but belongs to different user (not us)
        mock_db_session.select_one_or_none = AsyncMock(
            return_value=CharacterUserInfo(
                id=87654321, user_id=TEST_USER_UUID_2, name="Someone Else",
                corporation_id=None, alliance_id=None
            )
        )

        mock_sso_service.validate_jwt.return_value = MockCharacterInfo(
            character_id=87654321,
            character_name="Someone Else",
        )

        response = client.get(
            f"/auth/callback?code=link_code&state={link_state}",
            follow_redirects=False,
        )

        assert response.status_code == 401
