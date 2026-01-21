from __future__ import annotations

import secrets
from typing import Annotated

from litestar import Controller, Request, get, post
from litestar.di import Provide
from litestar.exceptions import NotAuthorizedException
from litestar.params import Dependency, Parameter
from litestar.response import Redirect

from api.auth.guards import require_auth
from config import Settings
from routes.auth.dependencies import ERR_AUTH_INVALID_STATE, auth_ext_rate_limit_config, auth_rate_limit_config
from routes.auth.service import AuthService, UserInfo, provide_auth_service
from services.encryption import provide_encryption_service
from services.eve_sso import EveSSOService


class AuthController(Controller):
    """Authentication endpoints for EVE SSO."""

    path = "/auth"
    middleware = [auth_rate_limit_config.middleware]
    dependencies = {
        "encryption_service": Provide(provide_encryption_service),
        "auth_service": Provide(provide_auth_service),
    }

    @get("/login")
    async def login(self, request: Request, sso_service: EveSSOService) -> Redirect:
        """Initiate EVE SSO login flow.

        Generates a random state parameter, stores it in session,
        and redirects to EVE SSO authorization page.
        """
        state = secrets.token_urlsafe(32)
        request.session["oauth_state"] = state
        request.session["linking"] = False

        auth_url = sso_service.get_authorization_url(state)

        return Redirect(path=auth_url)

    @get("/link", guards=[require_auth])
    async def link(self, request: Request, sso_service: EveSSOService) -> Redirect:
        """Initiate EVE SSO flow to link additional character.

        Requires authenticated user. Redirects to EVE SSO to authorize
        a new character that will be linked to the current account.
        """
        state = secrets.token_urlsafe(32)
        request.session["oauth_state"] = state
        request.session["linking"] = True

        auth_url = sso_service.get_authorization_url(state)

        return Redirect(path=auth_url)

    @get("/callback")
    async def callback(
        self,
        request: Request,
        auth_service: AuthService,
        code: str,
        app_settings: Annotated[Settings, Dependency(skip_validation=True)],
        oauth_state: str = Parameter(query="state"),
    ) -> Redirect:
        """Handle EVE SSO callback."""

        # Validate state parameter
        expected_state = request.session.get("oauth_state")
        if not expected_state or oauth_state != expected_state:
            raise NotAuthorizedException(ERR_AUTH_INVALID_STATE)

        # Clear state from session
        del request.session["oauth_state"]
        is_linking = request.session.pop("linking", False)

        try:
            result = await auth_service.process_callback(
                code=code,
                current_user=request.user,
                is_linking=is_linking,
            )
        except ValueError as e:
            raise NotAuthorizedException(str(e)) from e

        # Set session data (serialize UUID as string for consistent storage)
        request.session["user_id"] = str(result.user_id)
        request.session["character_id"] = result.character_id
        request.session["character_name"] = result.character_name

        return Redirect(path=app_settings.frontend_url)

    @post("/logout", middleware=[auth_ext_rate_limit_config.middleware])
    async def logout(self, request: Request) -> dict[str, bool]:
        """Log out current user by clearing session."""
        request.session.clear()
        return {"success": True}

    @get("/me", guards=[require_auth], middleware=[auth_ext_rate_limit_config.middleware])
    async def me(self, request: Request, auth_service: AuthService) -> UserInfo:
        """Get current authenticated user and their linked characters."""
        return await auth_service.get_current_user(request.user)
