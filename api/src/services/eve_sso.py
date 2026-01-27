"""EVE SSO OAuth2 authentication service.

This module provides OAuth2 authentication with EVE Online's SSO system,
including authorization URL generation, token exchange, token refresh, and
JWT validation.

Scope Groups
------------
ESI scopes are organized into logical groups for user-facing permission requests.
Rather than showing users a long list of individual scopes, we present grouped
permissions that map to application features:

- LOCATION: Scopes for tracking character location, online status, and current ship.
  Includes structure name resolution for player-owned structures.

- SEARCH: Scopes for character-authenticated search functionality.

The `has_scope_group()` function checks if all scopes in a group were granted,
enabling feature-gating based on granted permissions.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
from dataclasses import dataclass
from enum import StrEnum
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

# JWT subject claim prefix for character identification
# Format: "CHARACTER:EVE:<character_id>" e.g. "CHARACTER:EVE:123456789"
EVE_JWT_SUBJECT_PREFIX = "CHARACTER:EVE:"

BASE_SCOPES = [
    "publicData",
]

# PKCE code verifier length (43-128 characters per RFC 7636)
PKCE_VERIFIER_LENGTH = 64


def generate_pkce_pair() -> tuple[str, str]:
    """Generate a PKCE code verifier and challenge pair.

    Creates a cryptographically random code verifier and its corresponding
    SHA-256 challenge for use in the OAuth2 authorization flow.

    Returns:
        Tuple of (code_verifier, code_challenge)
    """
    # Generate random bytes and encode as URL-safe base64 (no padding)
    verifier_bytes = secrets.token_bytes(PKCE_VERIFIER_LENGTH)
    code_verifier = base64.urlsafe_b64encode(verifier_bytes).rstrip(b"=").decode("ascii")

    # Create SHA-256 hash of verifier, then base64url encode (no padding)
    challenge_digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(challenge_digest).rstrip(b"=").decode("ascii")

    return code_verifier, code_challenge


class _JWKSClientHolder:
    """Singleton holder for the JWKS client.

    PyJWKClient already caches keys internally, so sharing the instance
    across all EveSSOService instances is safe and efficient.
    """

    _instance: PyJWKClient | None = None

    @classmethod
    def get(cls) -> PyJWKClient:
        """Get the shared JWKS client singleton.

        The JWKS client fetches and caches the JSON Web Key Set from EVE SSO
        for validating JWT access tokens. Using a singleton ensures the key
        cache is shared across all service instances.

        Returns:
            Shared PyJWKClient instance
        """
        if cls._instance is None:
            cls._instance = PyJWKClient(EVE_SSO_JWKS_URL, cache_keys=True)
        return cls._instance


class ScopeGroup(StrEnum):
    """Optional ESI scope groups that can be requested during authorization."""

    LOCATION = "location"
    SEARCH = "search"


OPTIONAL_SCOPE_GROUPS: dict[ScopeGroup, list[str]] = {
    ScopeGroup.LOCATION: [
        "esi-location.read_location.v1",
        "esi-location.read_online.v1",
        "esi-location.read_ship_type.v1",
        "esi-universe.read_structures.v1",
    ],
    ScopeGroup.SEARCH: [
        "esi-search.search_structures.v1",
    ],
}


def build_scopes(scope_groups: list[ScopeGroup] | None = None) -> list[str]:
    """Build complete scope list from base + requested optional groups.

    Args:
        scope_groups: Optional list of scope group identifiers to include

    Returns:
        Combined list of unique scopes (base + optional groups)
    """
    if scope_groups is None:
        scope_groups = []
    return list(
        {
            *BASE_SCOPES,
            *(scope for group in scope_groups for scope in OPTIONAL_SCOPE_GROUPS.get(group, [])),
        }
    )


def has_scope_group(granted_scopes: list[str], group: ScopeGroup) -> bool:
    """Check if granted scopes include all scopes for a given group.

    Args:
        granted_scopes: List of scopes from refresh_token.scopes
        group: The scope group to check for

    Returns:
        True if all scopes in the group are present
    """
    required = OPTIONAL_SCOPE_GROUPS.get(group, [])
    return all(scope in granted_scopes for scope in required)


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
        self.client_id = client_id or settings.esi.client_id
        self.client_secret = client_secret or settings.esi.client_secret
        self.callback_url = callback_url or settings.eve_sso.callback_url
        self._http_client: httpx.AsyncClient | None = None

    @property
    def jwks_client(self) -> PyJWKClient:
        """Get the shared JWKS client for JWT validation."""
        return _JWKSClientHolder.get()

    def _build_auth_header(self) -> str:
        """Build HTTP Basic Auth header for EVE SSO token endpoint.

        Constructs the Base64-encoded "client_id:client_secret" credential
        string required for OAuth2 token requests to EVE SSO.

        Returns:
            Base64-encoded credentials for Authorization header
        """
        credentials = f"{self.client_id}:{self.client_secret}"
        return base64.b64encode(credentials.encode()).decode()

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create the shared HTTP client for SSO requests.

        Reuses a single httpx.AsyncClient instance for connection pooling
        and HTTP/2 multiplexing efficiency.

        Returns:
            Shared httpx.AsyncClient instance
        """
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    async def close(self) -> None:
        """Close the HTTP client.

        Should be called on application shutdown to cleanly close connections.
        """
        if self._http_client is not None and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None

    def get_authorization_url(self, state: str, scopes: list[str], code_challenge: str) -> str:
        """Build the EVE SSO authorization URL with PKCE.

        Args:
            state: Random string for CSRF protection
            scopes: List of ESI scopes to request
            code_challenge: PKCE code challenge (SHA-256 hash of code verifier)

        Returns:
            Full authorization URL to redirect user to
        """
        params = {
            "response_type": "code",
            "redirect_uri": self.callback_url,
            "client_id": self.client_id,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }

        if scopes:
            params["scope"] = " ".join(scopes)

        return f"{EVE_SSO_AUTHORIZE_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str, code_verifier: str) -> TokenResponse:
        """Exchange authorization code for access and refresh tokens.

        Args:
            code: Authorization code from SSO callback
            code_verifier: PKCE code verifier (original random string)

        Returns:
            TokenResponse with access_token, refresh_token, etc.

        Raises:
            httpx.HTTPStatusError: If token exchange fails
        """
        auth_header = self._build_auth_header()
        client = await self._get_http_client()

        response = await client.post(
            EVE_SSO_TOKEN_URL,
            headers={
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "authorization_code",
                "code": code,
                "code_verifier": code_verifier,
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
        auth_header = self._build_auth_header()
        client = await self._get_http_client()

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

        # Extract character ID from sub claim.
        # EVE SSO JWT subject format: "CHARACTER:EVE:<character_id>"
        # Example: "CHARACTER:EVE:123456789" -> character_id = 123456789
        # The format is defined by EVE SSO and has remained stable, but we
        # handle potential format changes by falling back to parsing the
        # entire subject as an integer if it doesn't match the expected pattern.
        sub = payload["sub"]
        character_id = (
            int(sub.removeprefix(EVE_JWT_SUBJECT_PREFIX)) if sub.startswith(EVE_JWT_SUBJECT_PREFIX) else int(sub)
        )

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
