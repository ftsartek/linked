from __future__ import annotations

import secrets
from dataclasses import dataclass
from uuid import UUID

from litestar import Controller, Request, delete, get, patch, put
from litestar.di import Provide
from litestar.exceptions import ClientException, NotFoundException
from litestar.response import Redirect
from litestar.status_codes import HTTP_204_NO_CONTENT

from api.auth.guards import require_auth
from routes.users.dependencies import ERR_CANNOT_DELETE_PRIMARY, ERR_CHARACTER_NOT_FOUND
from routes.users.service import (
    CharacterInfo,
    CharacterListResponse,
    UserService,
    provide_user_service,
)
from services.eve_sso import EveSSOService, provide_sso_service


@dataclass
class SetPrimaryCharacterRequest:
    """Request body for setting primary character."""

    character_id: int


@dataclass
class Viewport:
    """Viewport state for a map."""

    x: float
    y: float
    zoom: float


@dataclass
class UpdateSessionPreferencesRequest:
    """Request body for updating session preferences."""

    selected_map_id: UUID | None = None


@dataclass
class UpdateMapViewportRequest:
    """Request body for updating a map's viewport."""

    viewport: Viewport


@dataclass
class SessionPreferences:
    """User session preferences."""

    selected_map_id: UUID | None = None
    viewports: dict[str, Viewport] | None = None


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
            raise NotFoundException(ERR_CHARACTER_NOT_FOUND)
        return character

    @delete("/characters/{character_id:int}", status_code=HTTP_204_NO_CONTENT)
    async def delete_character(
        self,
        request: Request,
        user_service: UserService,
        character_id: int,
    ) -> None:
        """Delete a character and its refresh token.

        Cannot delete the user's last remaining character or primary character.
        """
        if not await user_service.can_delete_character(request.user.id):
            raise ClientException(
                "Cannot delete your last character. Link another character first or delete your account."
            )

        if await user_service.is_primary_character(request.user.id, character_id):
            raise ClientException(ERR_CANNOT_DELETE_PRIMARY)

        deleted = await user_service.delete_character(character_id, request.user.id)
        if not deleted:
            raise NotFoundException(ERR_CHARACTER_NOT_FOUND)

    @put("/primary-character", status_code=HTTP_204_NO_CONTENT)
    async def set_primary_character(
        self,
        request: Request,
        user_service: UserService,
        data: SetPrimaryCharacterRequest,
    ) -> None:
        """Set the user's primary character.

        The primary character is displayed in the navbar and used as the default identity.
        """
        success = await user_service.set_primary_character(request.user.id, data.character_id)
        if not success:
            raise NotFoundException(ERR_CHARACTER_NOT_FOUND)

    @get("/preferences")
    async def get_session_preferences(self, request: Request) -> SessionPreferences:
        """Get current session preferences (selected map, per-map viewports)."""
        selected_map_id = request.session.get("selected_map_id")
        viewports_data = request.session.get("viewports")

        viewports = None
        if viewports_data and isinstance(viewports_data, dict):
            viewports = {}
            for map_id, vp in viewports_data.items():
                if isinstance(vp, dict):
                    viewports[map_id] = Viewport(
                        x=vp.get("x", 0),
                        y=vp.get("y", 0),
                        zoom=vp.get("zoom", 1),
                    )

        return SessionPreferences(
            selected_map_id=UUID(selected_map_id) if selected_map_id else None,
            viewports=viewports,
        )

    @patch("/preferences", status_code=HTTP_204_NO_CONTENT)
    async def update_session_preferences(
        self,
        request: Request,
        data: UpdateSessionPreferencesRequest,
    ) -> None:
        """Update session preferences (selected map).

        Only provided fields are updated. Omitted fields are left unchanged.
        """
        if data.selected_map_id is not None:
            request.session["selected_map_id"] = str(data.selected_map_id)

    @patch("/preferences/maps/{map_id:uuid}/viewport", status_code=HTTP_204_NO_CONTENT)
    async def update_map_viewport(
        self,
        request: Request,
        map_id: UUID,
        data: UpdateMapViewportRequest,
    ) -> None:
        """Update the viewport for a specific map."""
        viewports = request.session.get("viewports", {})
        if not isinstance(viewports, dict):
            viewports = {}

        viewports[str(map_id)] = {
            "x": data.viewport.x,
            "y": data.viewport.y,
            "zoom": data.viewport.zoom,
        }
        request.session["viewports"] = viewports
