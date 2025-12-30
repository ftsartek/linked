from __future__ import annotations

import base64
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
import jwt
from jwt import PyJWKClient

from config import get_settings

# EVE SSO endpoints
EVE_SSO_AUTHORIZE_URL = "https://login.eveonline.com/v2/oauth/authorize"
EVE_SSO_TOKEN_URL = "https://login.eveonline.com/v2/oauth/token"
EVE_SSO_JWKS_URL = "https://login.eveonline.com/oauth/jwks"
EVE_SSO_ISSUER = "https://login.eveonline.com"


@dataclass
class TokenResponse:
    """Response from EVE SSO token endpoint."""

    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str


@dataclass
class CharacterInfo:
    """Character information extracted from JWT."""

    character_id: int
    character_name: str
    scopes: list[str]


class EveSSOService:
    """Service for EVE Online SSO OAuth2 authentication."""

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        callback_url: str | None = None,
    ) -> None:
        settings = get_settings()
        self.client_id = client_id or settings.eve_client_id
        self.client_secret = client_secret or settings.eve_client_secret
        self.callback_url = callback_url or settings.eve_callback_url
        self._jwks_client: PyJWKClient | None = None

    @property
    def jwks_client(self) -> PyJWKClient:
        """Get or create JWKS client for JWT validation."""
        if self._jwks_client is None:
            self._jwks_client = PyJWKClient(EVE_SSO_JWKS_URL, cache_keys=True)
        return self._jwks_client

    def get_authorization_url(self, state: str, scopes: list[str] | None = None) -> str:
        """Build the EVE SSO authorization URL.

        Args:
            state: Random string for CSRF protection
            scopes: List of ESI scopes to request (defaults to settings.eve_scopes)

        Returns:
            Full authorization URL to redirect user to
        """
        if scopes is None:
            scopes = get_settings().eve_scopes

        params = {
            "response_type": "code",
            "redirect_uri": self.callback_url,
            "client_id": self.client_id,
            "state": state,
        }

        if scopes:
            params["scope"] = " ".join(scopes)

        return f"{EVE_SSO_AUTHORIZE_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> TokenResponse:
        """Exchange authorization code for access and refresh tokens.

        Args:
            code: Authorization code from SSO callback

        Returns:
            TokenResponse with access_token, refresh_token, etc.

        Raises:
            httpx.HTTPStatusError: If token exchange fails
        """
        # Build basic auth header
        credentials = f"{self.client_id}:{self.client_secret}"
        auth_header = base64.b64encode(credentials.encode()).decode()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                EVE_SSO_TOKEN_URL,
                headers={
                    "Authorization": f"Basic {auth_header}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                },
            )
            response.raise_for_status()
            data = response.json()

        return TokenResponse(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_in=data["expires_in"],
            token_type=data["token_type"],
        )

    async def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        """Get new access token using refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            TokenResponse with new access_token and refresh_token

        Raises:
            httpx.HTTPStatusError: If refresh fails
        """
        credentials = f"{self.client_id}:{self.client_secret}"
        auth_header = base64.b64encode(credentials.encode()).decode()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                EVE_SSO_TOKEN_URL,
                headers={
                    "Authorization": f"Basic {auth_header}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                },
            )
            response.raise_for_status()
            data = response.json()

        return TokenResponse(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_in=data["expires_in"],
            token_type=data["token_type"],
        )

    def validate_jwt(self, access_token: str) -> CharacterInfo:
        """Validate JWT access token and extract character information.

        Args:
            access_token: JWT access token from EVE SSO

        Returns:
            CharacterInfo with character_id, name, and scopes

        Raises:
            jwt.InvalidTokenError: If token validation fails
        """
        # Get signing key from JWKS
        signing_key = self.jwks_client.get_signing_key_from_jwt(access_token)

        # Decode and validate the JWT
        payload = jwt.decode(
            access_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=["EVE Online", self.client_id],
            issuer=EVE_SSO_ISSUER,
            options={
                "require": ["exp", "iss", "sub", "aud"],
            },
        )

        # Extract character ID from sub claim (format: "CHARACTER:EVE:<character_id>")
        sub = payload["sub"]
        # Handle both old format "CHARACTER:EVE:123" and new format
        character_id = int(sub.split(":")[-1]) if sub.startswith("CHARACTER:EVE:") else int(sub)

        # Get character name
        character_name = payload.get("name", "")

        # Get scopes (can be string or list)
        scopes = payload.get("scp", [])
        if isinstance(scopes, str):
            scopes = [scopes] if scopes else []

        return CharacterInfo(
            character_id=character_id,
            character_name=character_name,
            scopes=scopes,
        )


async def provide_sso_service() -> EveSSOService:
    """Provide SSO service for dependency injection."""
    return EveSSOService()
