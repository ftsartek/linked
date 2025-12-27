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
    cors_allow_methods: list[str] = Field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE", "PATCH"])
    cors_allow_headers: list[str] = Field(default_factory=list)
    cors_allow_credentials: bool = False

    # Compression
    compression_minimum_size: int = 500
    compression_brotli_quality: int = 5

    # ESI
    esi_user_agent: str = Field(description="User-Agent for ESI requests (include app name and contact)")
    esi_timeout: float = 30.0

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