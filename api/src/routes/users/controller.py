from __future__ import annotations

import secrets

from litestar import Controller, Request, delete, get
from litestar.di import Provide
from litestar.exceptions import ClientException, NotFoundException
from litestar.response import Redirect
from litestar.status_codes import HTTP_204_NO_CONTENT

from api.auth.guards import require_auth
from routes.users.service import (
    CharacterInfo,
    CharacterListResponse,
    UserService,
    provide_user_service,
)
from services.eve_sso import EveSSOService, provide_sso_service


class UserController(Controller):
    """User account management endpoints."""

    path = "/users"
    guards = [require_auth]
    dependencies = {
        "sso_service": Provide(provide_sso_service),
        "user_service": Provide(provide_user_service),
    }

    @get("/characters/link")
    async def link_character(self, request: Request, sso_service: EveSSOService) -> Redirect:
        """Initiate EVE SSO flow to link additional character.

        Redirects to EVE SSO to authorize a new character
        that will be linked to the current account.
        """
        state = secrets.token_urlsafe(32)
        request.session["oauth_state"] = state
        request.session["linking"] = True

        auth_url = sso_service.get_authorization_url(state)

        return Redirect(path=auth_url)

    @get("/characters")
    async def list_characters(
        self,
        request: Request,
        user_service: UserService,
    ) -> CharacterListResponse:
        """Get all characters linked to current user."""
        characters = await user_service.get_user_characters(request.user.id)
        return CharacterListResponse(characters=characters)

    @get("/characters/{character_id:int}")
    async def get_character(
        self,
        request: Request,
        user_service: UserService,
        character_id: int,
    ) -> CharacterInfo:
        """Get character details including corporation and alliance."""
        character = await user_service.get_character(character_id, request.user.id)
        if character is None:
            raise NotFoundException("Character not found")
        return character

    @delete("/characters/{character_id:int}", status_code=HTTP_204_NO_CONTENT)
    async def delete_character(
        self,
        request: Request,
        user_service: UserService,
        character_id: int,
    ) -> None:
        """Delete a character and its refresh token.

        Cannot delete the user's last remaining character.
        """
        if not await user_service.can_delete_character(request.user.id):
            raise ClientException(
                "Cannot delete your last character. Link another character first or delete your account."
            )

        deleted = await user_service.delete_character(character_id, request.user.id)
        if not deleted:
            raise NotFoundException("Character not found")
