from __future__ import annotations

import secrets
import warnings
from functools import lru_cache
from importlib import metadata
from os import getenv
from pathlib import Path
from typing import Literal

from cryptography.fernet import Fernet
from msgspec import Struct, field

from .loader import ConfigLoader

__VERSION__ = metadata.version("linked-eve")


class BaseStruct(Struct, omit_defaults=False, kw_only=True):
    """Base struct with common configuration."""

    pass


class CSRFSettings(BaseStruct):
    """CSRF settings."""

    secret: str = ""

    def __post_init__(self) -> None:
        self.secret = getenv("CSRF_SECRET", "") or self.secret
        if not self.secret:
            warnings.warn("CSRF secret is not set, autogenerating.")
            self.secret = secrets.token_urlsafe(32)


class CORSSettings(BaseStruct):
    """CORS settings."""

    allow_origins: list[str] = field(default_factory=list)
    allow_methods: list[Literal["GET", "POST", "DELETE", "PATCH", "PUT", "HEAD", "TRACE", "OPTIONS", "*"]] = field(
        default_factory=lambda: [
            "GET",
            "POST",
            "PUT",
            "DELETE",
            "PATCH",
            "OPTIONS",
        ]
    )
    allow_headers: list[str] = field(default_factory=list)
    allow_credentials: bool = True


class CompressionSettings(BaseStruct):
    """Response compression settings."""

    minimum_size: int = 500
    brotli_quality: int = 5


class ESISettings(BaseStruct):
    """EVE ESI API settings."""

    contact_email: str = ""
    timeout: float = 30.0
    client_secret: str = ""
    client_id: str = ""

    @property
    def user_agent(self) -> str:
        return f"LinkedEVE/{__VERSION__} ({self.contact_email})"

    def __post_init__(self) -> None:
        self.client_secret = getenv("EVE_CLIENT_SECRET", "") or self.client_secret
        if not self.client_secret:
            warnings.warn("EVE client secret is not set.")

        if not self.client_id:
            warnings.warn("EVE client ID is not set.")

        if not self.contact_email:
            warnings.warn("ESI contact email is not set.")


class EVESSOSettings(BaseStruct):
    """EVE SSO authentication settings."""

    callback_url: str = "http://localhost:8000/auth/callback"
    token_encryption_key: str = ""

    def __post_init__(self) -> None:
        self.token_encryption_key = getenv("TOKEN_ENCRYPTION_KEY", "") or self.token_encryption_key
        if not self.token_encryption_key:
            warnings.warn("Token encryption key is not set, autogenerating.")
            self.token_encryption_key = Fernet.generate_key().decode()


class ValkeySettings(BaseStruct):
    """Valkey (Redis-compatible) settings."""

    password: str = ""
    host: str = "localhost"
    port: int = 6379
    session_db: int = 0
    event_db: int = 1
    user: str = "default"

    def __post_init__(self) -> None:
        env_pass = getenv("VALKEY_PASSWORD")
        if env_pass:
            self.password = env_pass

    @property
    def session_url(self) -> str:
        """Build Valkey URL for session storage."""
        if self.password:
            return f"valkey://{self.user}:{self.password}@{self.host}:{self.port}/{self.session_db}"
        return f"valkey://{self.user}@{self.host}:{self.port}/{self.session_db}"

    @property
    def event_url(self) -> str:
        """Build Valkey URL for event storage."""
        if self.password:
            return f"valkey://{self.user}:{self.password}@{self.host}:{self.port}/{self.event_db}"
        return f"valkey://{self.user}@{self.host}:{self.port}/{self.event_db}"


class SessionSettings(BaseStruct):
    """Session management settings."""

    max_age: int = 604800  # 7 days in seconds


class RateLimitSettings(BaseStruct):
    """Rate limiting settings."""

    # Auth endpoints (login, link, callback) - stricter limit
    auth_requests_per_minute: int = 10
    # Extended auth endpoints (me, logout) - more lenient
    auth_extended_requests_per_minute: int = 180


class ImageCacheSettings(BaseStruct):
    """Image cache settings."""

    dir: str = "/var/cache/linked/images"
    ttl_seconds: int = 259200  # 3 days


class PostgresSettings(BaseStruct):
    """Database connection settings."""

    password: str = ""
    host: str = "localhost"
    port: int = 5432
    user: str = "postgres"
    name: str = "linked"
    pool_min_size: int = 5
    pool_max_size: int = 20
    ssl: bool = False

    def __post_init__(self) -> None:
        env_pass = getenv("POSTGRES_PASSWORD")
        if env_pass:
            self.password = env_pass

    @property
    def uri(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class DataSettings(BaseStruct):
    """Data directory settings."""

    dir: str = "/var/lib/linked/preseed"

    @property
    def base_dir(self) -> Path:
        """Base directory path."""
        return Path(self.dir)

    @property
    def static_dir(self) -> Path:
        """Static directory path (baked in, up 3)."""
        return Path(__file__).parent.parent.parent / "static"

    @property
    def curated_dir(self) -> Path:
        """Curated data directory within static."""
        return self.static_dir / "preseed" / "curated"

    @property
    def sde_dir(self) -> Path:
        """SDE data directory within data_dir."""
        return Path(self.base_dir) / "sde"


class Settings(BaseStruct):
    """Application settings."""

    debug: bool = False
    frontend_url: str = "http://localhost:5173"

    csrf: CSRFSettings = field(default_factory=lambda: CSRFSettings())
    cors: CORSSettings = field(default_factory=lambda: CORSSettings())
    compression: CompressionSettings = field(default_factory=lambda: CompressionSettings())
    esi: ESISettings = field(default_factory=lambda: ESISettings())
    eve_sso: EVESSOSettings = field(default_factory=lambda: EVESSOSettings())
    valkey: ValkeySettings = field(default_factory=lambda: ValkeySettings())
    session: SessionSettings = field(default_factory=lambda: SessionSettings())
    rate_limit: RateLimitSettings = field(default_factory=lambda: RateLimitSettings())
    image_cache: ImageCacheSettings = field(default_factory=lambda: ImageCacheSettings())
    postgres: PostgresSettings = field(default_factory=lambda: PostgresSettings())
    data: DataSettings = field(default_factory=lambda: DataSettings())


@lru_cache
def get_settings() -> Settings:
    """Load settings from config file."""
    loader = ConfigLoader(
        mapped_class=Settings,
        source_file=Path("config.yaml"),
        source_override_env="CONFIG_FILE",
    )
    return loader.get_config()
