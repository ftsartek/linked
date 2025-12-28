from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Iterator
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from litestar import Litestar
from litestar.di import Provide
from sqlspec import AsyncDriverAdapterBase
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

from api.auth import AuthenticationMiddleware
from routes import AuthController

# Test UUID constants
TEST_USER_UUID = UUID("00000000-0000-0000-0000-000000000001")
TEST_USER_UUID_2 = UUID("00000000-0000-0000-0000-000000000002")


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
    # Patch in both locations: controller (for login/link) and service (for callback)
    with (
        patch("routes.auth.controller.get_sso_service") as mock_controller,
        patch("routes.auth.service.get_sso_service") as mock_service_module,
    ):
        mock_service = MagicMock()
        mock_service.get_authorization_url.return_value = "https://login.eveonline.com/v2/oauth/authorize?mock=true"
        mock_service.exchange_code = AsyncMock(return_value=MockTokenResponse())
        mock_service.validate_jwt.return_value = MockCharacterInfo()
        mock_controller.return_value = mock_service
        mock_service_module.return_value = mock_service
        yield mock_service


@pytest.fixture
def mock_encryption_service() -> Iterator[MagicMock]:
    """Mock the encryption service."""
    with patch("routes.auth.service.get_encryption_service") as mock_get:
        mock_service = MagicMock()
        mock_service.encrypt.return_value = b"encrypted_token"
        mock_service.decrypt.return_value = "decrypted_token"
        mock_get.return_value = mock_service
        yield mock_service


class MockDbSession(AsyncDriverAdapterBase):  # type: ignore[misc]
    """Mock database session that satisfies type checking."""

    def __init__(self) -> None:
        self.execute = AsyncMock(return_value=MagicMock(fetchall=AsyncMock(return_value=[])))
        self.select_one_or_none = AsyncMock(return_value=None)
        self.select_value = AsyncMock(return_value=TEST_USER_UUID)
        self.select = AsyncMock(return_value=[])


@pytest.fixture
def mock_db_session() -> MockDbSession:
    """Create a mock database session for dependency injection."""
    return MockDbSession()


@pytest.fixture
def test_app(mock_db_session: MockDbSession) -> Litestar:
    """Create a test Litestar app with in-memory session store."""
    session_config = ServerSideSessionConfig(
        key="session",
        max_age=3600,
    )

    auth_middleware = DefineMiddleware(
        AuthenticationMiddleware,
        exclude=["^/schema"],
    )

    # Provide mock db_session as a dependency
    def provide_mock_db_session() -> Any:
        return mock_db_session

    return Litestar(
        route_handlers=[AuthController],
        stores={"sessions": MemoryStore()},
        middleware=[session_config.middleware, auth_middleware],
        dependencies={"db_session": Provide(provide_mock_db_session, sync_to_thread=False)},
        debug=True,
    )


@pytest.fixture
def client(
    test_app: Litestar,
    mock_sso_service: MagicMock,
    mock_encryption_service: MagicMock,
) -> Iterator[TestClient]:
    """Create a test client with all mocks in place."""
    with TestClient(app=test_app) as client:
        yield client
