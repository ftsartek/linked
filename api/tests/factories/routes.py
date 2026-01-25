"""Test-only routes for integration testing.

These routes are only included in the test app and provide utilities
for setting up test state that would normally require session injection.
"""

from __future__ import annotations

from litestar import Request, Router, get
from litestar.params import Parameter

from services.eve_sso import ScopeGroup


@get("/test/auth-setup")
async def auth_setup(
    request: Request,
    scope_groups: list[ScopeGroup] | None = Parameter(query="scopes", default=None),
    linking: bool = Parameter(query="linking", default=False),
) -> dict[str, str | list[str] | bool]:
    """Set up oauth_state in session for testing authentication flow.

    This endpoint simulates what /auth/login does (setting oauth_state)
    without requiring a browser redirect to EVE SSO.

    Args:
        scope_groups: Optional list of scope groups to request (e.g., ?scopes=location)
        linking: Whether this is a character linking operation

    Returns:
        Dict with the oauth state value and settings to use in the callback
    """
    state = "test_oauth_state"
    request.session["oauth_state"] = state
    request.session["linking"] = linking
    if scope_groups:
        request.session["scope_groups"] = [str(g) for g in scope_groups]
    return {
        "state": state,
        "linking": linking,
        "scope_groups": [str(g) for g in scope_groups] if scope_groups else [],
    }


test_router = Router(path="/", route_handlers=[auth_setup])
