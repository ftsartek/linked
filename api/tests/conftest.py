from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Iterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from litestar import Litestar
from litestar.middleware.session.server_side import ServerSideSessionConfig
from litestar.stores.memory import MemoryStore
from litestar.testing import TestClient
from litestar.middleware import DefineMiddleware

# Set test environment variables before importing app modules
os.environ.setdefault("LINKED_CSRF_SECRET", "test_csrf_secret_at_least_32_chars_long")
os.environ.setdefault("LINKED_EVE_CLIENT_ID", "test_client_id")
os.environ.setdefault("LINKED_EVE_CLIENT_SECRET", "test_client_secret")
os.environ.setdefault("LINKED_TOKEN_ENCRYPTION_KEY", "dGVzdF9lbmNyeXB0aW9uX2tleV8zMl9jaGFycw==")  # base64 test key
os.environ.setdefault("LINKED_ESI_USER_AGENT", "test-agent")

from api.auth import AuthController, AuthenticationMiddleware


@dataclass
class MockTokenResponse:
    """Mock token response from EVE SSO."""

    access_token: str = "mock_access_token"
    refresh_token: str = "mock_refresh_token"
    expires_in: int = 1200
    token_type: str = "Bearer"


@dataclass
class MockCharacterInfo:
    """Mock character info from JWT validation."""

    character_id: int = 12345678
    character_name: str = "Test Pilot"
    scopes: list[str] | None = None

    def __post_init__(self) -> None:
        if self.scopes is None:
            self.scopes = []


@pytest.fixture
def mock_sso_service() -> Iterator[MagicMock]:
    """Mock the EVE SSO service."""
    with patch("api.auth.routes.get_sso_service") as mock_get:
        mock_service = MagicMock()
        mock_service.get_authorization_url.return_value = "https://login.eveonline.com/v2/oauth/authorize?mock=true"
        mock_service.exchange_code = AsyncMock(return_value=MockTokenResponse())
        mock_service.validate_jwt.return_value = MockCharacterInfo()
        mock_get.return_value = mock_service
        yield mock_service


@pytest.fixture
def mock_encryption_service() -> Iterator[MagicMock]:
    """Mock the encryption service."""
    with patch("api.auth.routes.get_encryption_service") as mock_get:
        mock_service = MagicMock()
        mock_service.encrypt.return_value = b"encrypted_token"
        mock_service.decrypt.return_value = "decrypted_token"
        mock_get.return_value = mock_service
        yield mock_service


@pytest.fixture
def mock_db_session() -> Iterator[MagicMock]:
    """Mock the database session."""
    with patch("api.auth.routes.provide_session") as mock_provide:
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone = AsyncMock(return_value=None)
        mock_result.fetchall = AsyncMock(return_value=[])
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Make the context manager work
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cm.__aexit__ = AsyncMock(return_value=None)
        mock_provide.return_value = mock_cm

        yield mock_session


@pytest.fixture
def test_app() -> Litestar:
    """Create a test Litestar app with in-memory session store."""
    session_config = ServerSideSessionConfig(
        key="session",
        max_age=3600,
    )

    auth_middleware = DefineMiddleware(
        AuthenticationMiddleware,
        exclude=["^/schema"],
    )

    return Litestar(
        route_handlers=[AuthController],
        stores={"sessions": MemoryStore()},
        middleware=[session_config.middleware, auth_middleware],
        debug=True,
    )


@pytest.fixture
def client(
    test_app: Litestar,
    mock_sso_service: MagicMock,
    mock_encryption_service: MagicMock,
    mock_db_session: MagicMock,
) -> Iterator[TestClient]:
    """Create a test client with all mocks in place."""
    with TestClient(app=test_app) as client:
        yield client
