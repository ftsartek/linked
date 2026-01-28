from __future__ import annotations

import secrets
from dataclasses import dataclass
from uuid import UUID

from litestar import Controller, Request, Response, delete, get, patch, post, put
from litestar.di import Provide
from litestar.exceptions import ClientException, NotFoundException
from litestar.openapi import ResponseSpec
from litestar.params import Parameter
from litestar.response import Redirect
from litestar.status_codes import (
    HTTP_204_NO_CONTENT,
    HTTP_403_FORBIDDEN,
    HTTP_424_FAILED_DEPENDENCY,
    HTTP_503_SERVICE_UNAVAILABLE,
)

from api.auth.guards import require_acl_access, require_auth
from api.di.valkey import provide_location_cache
from routes.users.dependencies import ERR_CANNOT_DELETE_PRIMARY, ERR_CHARACTER_NOT_FOUND
from routes.users.location import (
    CharacterLocationData,
    CharacterLocationError,
    LocationService,
    provide_location_service,
)
from routes.users.service import (
    CharacterInfo,
    CharacterListResponse,
    UserService,
    provide_user_service,
)
from services.encryption import provide_encryption_service
from services.eve_sso import EveSSOService, ScopeGroup, build_scopes, generate_pkce_pair


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
    guards = [require_auth, require_acl_access]
    dependencies = {
        "user_service": Provide(provide_user_service),
        "encryption_service": Provide(provide_encryption_service),
        "location_service": Provide(provide_location_service),
        "location_cache": Provide(provide_location_cache),
    }

    @get("/characters/link")
    async def link_character(
        self,
        request: Request,
        sso_service: EveSSOService,
        scope_groups: list[ScopeGroup] | None = Parameter(query="scopes", default=None),
    ) -> Redirect:
        """Initiate EVE SSO flow to link additional character.

        Redirects to EVE SSO to authorize a new character
        that will be linked to the current account.

        Args:
            scope_groups: Optional list of additional scope groups to request.
                Valid values: "location". Example: ?scopes=location
        """
        state = secrets.token_urlsafe(32)
        code_verifier, code_challenge = generate_pkce_pair()

        request.session["oauth_state"] = state
        request.session["code_verifier"] = code_verifier
        request.session["linking"] = True
        if scope_groups:
            request.session["scope_groups"] = [str(g) for g in scope_groups]

        scopes = build_scopes(scope_groups)
        auth_url = sso_service.get_authorization_url(state, scopes=scopes, code_challenge=code_challenge)

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

    @post(
        "/characters/{character_id:int}/location/refresh",
        responses={
            HTTP_403_FORBIDDEN: ResponseSpec(
                data_container=CharacterLocationError,
                description="No location scope or token expired/revoked",
            ),
            HTTP_424_FAILED_DEPENDENCY: ResponseSpec(
                data_container=CharacterLocationError,
                description="Missing reference data - ESI/ESD not synced",
            ),
            HTTP_503_SERVICE_UNAVAILABLE: ResponseSpec(
                data_container=CharacterLocationError,
                description="ESI service unavailable",
            ),
        },
    )
    async def refresh_character_location(
        self,
        request: Request,
        location_service: LocationService,
        character_id: int,
    ) -> CharacterLocationData | CharacterLocationError:
        """Refresh location data for a specific character.

        Fetches current location, online status, and ship information
        for a character that has the location scope enabled.

        Data is cached with stale-while-revalidate pattern:
        - Location: 10 second stale threshold
        - Online/Ship: 60 second stale threshold

        Returns:
            CharacterLocationData on success, CharacterLocationError on scope/token issues
        """
        result = await location_service.refresh_character_location(character_id, request.user.id)
        if result is None:
            raise NotFoundException(ERR_CHARACTER_NOT_FOUND)

        # Return appropriate status codes for error types
        if isinstance(result, CharacterLocationError):
            if result.error in ("no_scope", "token_expired", "token_revoked"):
                # Authorization/authentication failure
                return Response(content=result, status_code=HTTP_403_FORBIDDEN)  # type: ignore[return-value]
            if result.error == "server_error":
                # Missing reference data - ESI/ESD not synced
                return Response(content=result, status_code=HTTP_424_FAILED_DEPENDENCY)  # type: ignore[return-value]
            if result.error == "esi_error":
                # ESI service unavailable
                return Response(content=result, status_code=HTTP_503_SERVICE_UNAVAILABLE)  # type: ignore[return-value]

        return result
