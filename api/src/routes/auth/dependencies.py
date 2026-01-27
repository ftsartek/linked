from __future__ import annotations

from litestar.middleware.rate_limit import RateLimitConfig

from config import get_settings

# Error messages
ERR_AUTH_INVALID_STATE = "Invalid state parameter"


def _get_auth_rate_limit_config() -> RateLimitConfig:
    """Get rate limit config for auth endpoints using settings."""
    settings = get_settings()
    return RateLimitConfig(
        rate_limit=("minute", settings.rate_limit.auth_requests_per_minute),
        exclude=["/auth/logout", "/auth/me"],
        store="rate_limit",
    )


def _get_auth_ext_rate_limit_config() -> RateLimitConfig:
    """Get rate limit config for extended auth endpoints using settings."""
    settings = get_settings()
    return RateLimitConfig(
        rate_limit=("minute", settings.rate_limit.auth_extended_requests_per_minute),
        store="rate_limit",
    )


# Rate limit configs - loaded lazily to use settings
# These are accessed at module import time by controllers, so we use a property-like pattern
auth_rate_limit_config = _get_auth_rate_limit_config()
auth_ext_rate_limit_config = _get_auth_ext_rate_limit_config()
