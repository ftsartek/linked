from __future__ import annotations

import os
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from litestar import Litestar
from litestar.di import Provide
from litestar.middleware import DefineMiddleware
from litestar.middleware.session.server_side import ServerSideSessionConfig
from litestar.stores.memory import MemoryStore
from litestar.testing import TestClient
from sqlspec import AsyncDriverAdapterBase

# Set test environment variables before importing app modules
os.environ.setdefault("LINKED_CSRF_SECRET", "test_csrf_secret_at_least_32_chars_long")
os.environ.setdefault("LINKED_EVE_CLIENT_ID", "test_client_id")
os.environ.setdefault("LINKED_EVE_CLIENT_SECRET", "test_client_secret")
os.environ.setdefault("LINKED_TOKEN_ENCRYPTION_KEY", "dGVzdF9lbmNyeXB0aW9uX2tleV8zMl9jaGFycw==")  # base64 test key
os.environ.setdefault("LINKED_ESI_USER_AGENT", "test-agent")

from api.auth import AuthenticationMiddleware
from routes import AuthController
from services.encryption import EncryptionService
from services.eve_sso import EveSSOService

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


class MockSSOService(EveSSOService):
    """Mock SSO service for testing."""

    def __init__(self) -> None:
        # Don't call super().__init__() to avoid loading settings
        self.client_id = "test_client_id"
        self.client_secret = "test_client_secret"
        self.callback_url = "http://localhost/callback"
        self._jwks_client = None

    def get_authorization_url(self, state: str, scopes: list[str] | None = None) -> str:
        return "https://login.eveonline.com/v2/oauth/authorize?mock=true"

    async def exchange_code(self, code: str) -> MockTokenResponse:
        return MockTokenResponse()

    def validate_jwt(self, access_token: str) -> MockCharacterInfo:
        return MockCharacterInfo()


@pytest.fixture
def mock_sso_service() -> MockSSOService:
    """Mock the EVE SSO service."""
    return MockSSOService()


class MockEncryptionService(EncryptionService):
    """Mock encryption service for testing."""

    def __init__(self) -> None:
        # Don't call super().__init__() to avoid loading settings
        pass

    def encrypt(self, plaintext: str) -> bytes:
        return b"encrypted_token"

    def decrypt(self, ciphertext: bytes) -> str:
        return "decrypted_token"


@pytest.fixture
def mock_encryption_service() -> MockEncryptionService:
    """Mock the encryption service."""
    return MockEncryptionService()


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
def test_app(
    mock_db_session: MockDbSession,
    mock_sso_service: MockSSOService,
    mock_encryption_service: MockEncryptionService,
) -> Litestar:
    """Create a test Litestar app with in-memory session store."""
    session_config = ServerSideSessionConfig(
        key="session",
        max_age=3600,
    )

    auth_middleware = DefineMiddleware(
        AuthenticationMiddleware,
        exclude=["^/schema"],
    )

    # Provide mock dependencies
    def provide_mock_db_session() -> Any:
        return mock_db_session

    async def provide_mock_sso_service() -> MockSSOService:
        return mock_sso_service

    async def provide_mock_encryption_service() -> MockEncryptionService:
        return mock_encryption_service

    return Litestar(
        route_handlers=[AuthController],
        stores={"sessions": MemoryStore()},
        middleware=[session_config.middleware, auth_middleware],
        dependencies={
            "db_session": Provide(provide_mock_db_session, sync_to_thread=False),
            "sso_service": Provide(provide_mock_sso_service),
            "encryption_service": Provide(provide_mock_encryption_service),
        },
        debug=True,
    )


@pytest.fixture
def client(test_app: Litestar) -> Iterator[TestClient]:
    """Create a test client with all mocks in place."""
    with TestClient(app=test_app) as client:
        yield client
