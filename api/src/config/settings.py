from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from litestar.types import Method
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    debug: bool = False

    # CSRF
    csrf_secret: str = Field(min_length=32)

    # CORS
    cors_allow_origins: list[str] = Field(default_factory=list)
    cors_allow_methods: list[Method | Literal["*"]] = Field(
        default_factory=lambda: ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
    )
    cors_allow_headers: list[str] = Field(default_factory=list)
    cors_allow_credentials: bool = True

    # Compression
    compression_minimum_size: int = 500
    compression_brotli_quality: int = 5

    # ESI
    esi_user_agent: str = Field(description="User-Agent for ESI requests (include app name and contact)")
    esi_timeout: float = 30.0

    # EVE SSO
    eve_client_id: str = Field(description="EVE SSO application client ID")
    eve_client_secret: str = Field(description="EVE SSO application client secret")
    eve_callback_url: str = "http://localhost:8000/auth/callback"
    # TODO: Actually set these to useful values
    eve_scopes: list[str] = Field(
        default_factory=lambda: [
            "publicData",
            "esi-search.search_structures.v1",
            "esi-corporations.read_corporation_membership.v1",
            "esi-corporations.read_structures.v1",
            "esi-corporations.track_members.v1",
            "esi-corporations.read_divisions.v1",
            "esi-corporations.read_standings.v1",
            "esi-planets.read_customs_offices.v1",
            "esi-corporations.read_facilities.v1",
            "esi-universe.read_structures.v1",
            "esi-corporations.read_starbases.v1",
        ],
        description="ESI scopes to request",
    )

    # Valkey
    valkey_host: str = "localhost"
    valkey_port: int = 6379
    valkey_session_db: int = 0
    valkey_event_db: int = 1
    valkey_user: str = "default"
    valkey_password: str | None = None
    session_max_age: int = 604800  # 7 days in seconds

    @property
    def valkey_session_url(self) -> str:
        """Build Valkey URL for session storage."""
        if self.valkey_password:
            return f"valkey://{self.valkey_user}:{self.valkey_password}@{self.valkey_host}:{self.valkey_port}/{self.valkey_session_db}"
        return f"valkey://{self.valkey_user}@{self.valkey_host}:{self.valkey_port}/{self.valkey_session_db}"

    @property
    def valkey_event_url(self) -> str:
        """Build Valkey URL for event storage."""
        if self.valkey_password:
            return f"valkey://{self.valkey_user}:{self.valkey_password}@{self.valkey_host}:{self.valkey_port}/{self.valkey_session_db}"
        return f"valkey://{self.valkey_user}@{self.valkey_host}:{self.valkey_port}/{self.valkey_event_db}"

    # Token encryption (Fernet key, generate with:
    # python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    token_encryption_key: str = Field(
        min_length=32,
        description="Fernet key for encrypting refresh tokens",
    )

    # Frontend redirect URL after auth
    frontend_url: str = "http://localhost:5173"

    # Image cache
    image_cache_dir: str = "/var/cache/linked/images"
    image_cache_ttl_seconds: int = 259200  # 3 days

    # Database
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "linked"
    db_password: str = ""
    db_name: str = "linked"
    db_pool_min_size: int = 5
    db_pool_max_size: int = 20
    db_ssl: bool = False

    # Data directories
    data_dir: Path = Path("/var/lib/linked/preseed")

    @property
    def static_dir(self) -> Path:
        """Static directory path (baked in, up 3)"""
        return Path(__file__).parent.parent.parent / "static"

    @property
    def curated_dir(self) -> Path:
        """Curated data directory within static."""
        return self.static_dir / "preseed" / "curated"

    @property
    def sde_dir(self) -> Path:
        """SDE data directory within data_dir."""
        return self.data_dir / "sde"


@lru_cache
def get_settings() -> Settings:
    # Required fields are loaded from environment variables by pydantic-settings
    return Settings()  # type: ignore[call-arg]
