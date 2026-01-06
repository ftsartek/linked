from __future__ import annotations

from litestar.middleware.rate_limit import RateLimitConfig

# Error messages
ERR_AUTH_INVALID_STATE = "Invalid state parameter"

# Rate limit: 10 requests per minute for auth endpoints
# Excludes /auth/logout to prevent issues during logout flows
# Uses the "rate_limit" store registered in app.py
auth_rate_limit_config = RateLimitConfig(
    rate_limit=("minute", 10),
    exclude=["/auth/logout"],
    store="rate_limit",
)
