"""Test-only routes for integration testing.

These routes are only included in the test app and provide utilities
for setting up test state that would normally require session injection.
"""

from __future__ import annotations

from litestar import Request, Router, get


@get("/test/auth-setup")
async def auth_setup(request: Request) -> dict[str, str]:
    """Set up oauth_state in session for testing authentication flow.

    This endpoint simulates what /auth/login does (setting oauth_state)
    without requiring a browser redirect to EVE SSO.

    Returns:
        Dict with the oauth state value to use in the callback
    """
    state = "test_oauth_state"
    request.session["oauth_state"] = state
    request.session["linking"] = False
    return {"state": state}


test_router = Router(path="/", route_handlers=[auth_setup])
