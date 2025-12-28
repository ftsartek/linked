from __future__ import annotations

import secrets

from litestar import Controller, Request, get, post
from litestar.di import Provide
from litestar.exceptions import NotAuthorizedException
from litestar.params import Parameter
from litestar.response import Redirect

from api.auth.guards import require_auth
from config import get_settings
from routes.auth.service import AuthService, UserInfo, provide_auth_service
from services.eve_sso import get_sso_service


class AuthController(Controller):
    """Authentication endpoints for EVE SSO."""

    path = "/auth"
    dependencies = {"auth_service": Provide(provide_auth_service, sync_to_thread=False)}

    @get("/login")
    async def login(self, request: Request) -> Redirect:
        """Initiate EVE SSO login flow.

        Generates a random state parameter, stores it in session,
        and redirects to EVE SSO authorization page.
        """
        state = secrets.token_urlsafe(32)
        request.session["oauth_state"] = state
        request.session["linking"] = False

        sso = get_sso_service()
        auth_url = sso.get_authorization_url(state)

        return Redirect(path=auth_url)

    @get("/link", guards=[require_auth])
    async def link(self, request: Request) -> Redirect:
        """Initiate EVE SSO flow to link additional character.

        Requires authenticated user. Redirects to EVE SSO to authorize
        a new character that will be linked to the current account.
        """
        state = secrets.token_urlsafe(32)
        request.session["oauth_state"] = state
        request.session["linking"] = True

        sso = get_sso_service()
        auth_url = sso.get_authorization_url(state)

        return Redirect(path=auth_url)

    @get("/callback")
    async def callback(
        self,
        request: Request,
        auth_service: AuthService,
        code: str,
        oauth_state: str = Parameter(query="state"),
    ) -> Redirect:
        """Handle EVE SSO callback."""
        settings = get_settings()

        # Validate state parameter
        expected_state = request.session.get("oauth_state")
        if not expected_state or oauth_state != expected_state:
            raise NotAuthorizedException("Invalid state parameter")

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

        # Set session data
        request.session["user_id"] = result.user_id
        request.session["character_id"] = result.character_id
        request.session["character_name"] = result.character_name

        return Redirect(path=settings.frontend_url)

    @post("/logout")
    async def logout(self, request: Request) -> dict[str, bool]:
        """Log out current user by clearing session."""
        request.session.clear()
        return {"success": True}

    @get("/me", guards=[require_auth])
    async def me(self, request: Request, auth_service: AuthService) -> UserInfo:
        """Get current authenticated user and their linked characters."""
        return await auth_service.get_current_user(request.user)
