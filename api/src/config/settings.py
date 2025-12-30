from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LINKED_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    debug: bool = False

    # CSRF
    csrf_secret: str = Field(min_length=32)

    # CORS
    cors_allow_origins: list[str] = Field(default_factory=list)
    cors_allow_methods: list[str] = Field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
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

    # Session
    valkey_url: str = "valkey://localhost:6379/0"
    session_max_age: int = 604800  # 7 days in seconds

    # Token encryption (Fernet key, generate with:
    # python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    token_encryption_key: str = Field(min_length=32, description="Fernet key for encrypting refresh tokens")

    # Frontend redirect URL after auth
    frontend_url: str = "http://localhost:5173"

    # Database
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "linked"
    db_password: str = ""
    db_name: str = "linked"
    db_pool_min_size: int = 5
    db_pool_max_size: int = 20


@lru_cache
def get_settings() -> Settings:
    return Settings()
