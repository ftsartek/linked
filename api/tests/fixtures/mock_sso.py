"""Mock EVE SSO service for testing.

Provides a mock implementation of EveSSOService that skips cryptographic
JWT validation and doesn't make real HTTP requests to EVE SSO endpoints.
"""

from __future__ import annotations

import base64
import json

from services.eve_sso import CharacterInfo, EveSSOService, TokenResponse


class MockEveSSOService(EveSSOService):
    """Mock SSO service for testing - skips cryptographic JWT validation.

    This service is used in test environments where we don't want to
    hit the real EVE SSO endpoints or validate real JWTs. It decodes
    mock tokens that use a simple base64-encoded payload format.

    Mock token format: header.payload.signature
    - header: base64-encoded JSON with {"alg": "none"}
    - payload: base64-encoded JSON with sub, name, scp fields
    - signature: any string (not validated)
    """

    def validate_jwt(self, access_token: str) -> CharacterInfo:
        """Extract character info from mock token without cryptographic validation.

        Args:
            access_token: Mock JWT token in format header.payload.signature

        Returns:
            CharacterInfo with character_id, name, and scopes

        Raises:
            ValueError: If token format is invalid
        """
        parts = access_token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid token format: expected header.payload.signature")

        # Decode the payload (add padding if needed)
        payload_b64 = parts[1]
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding

        payload = json.loads(base64.urlsafe_b64decode(payload_b64))

        # Extract character ID from sub claim (format: "CHARACTER:EVE:<character_id>")
        sub = payload["sub"]
        character_id = int(sub.split(":")[-1]) if sub.startswith("CHARACTER:EVE:") else int(sub)

        # Get scopes (can be string or list)
        scopes = payload.get("scp", [])
        if isinstance(scopes, str):
            scopes = [scopes] if scopes else []

        return CharacterInfo(
            character_id=character_id,
            character_name=payload.get("name", ""),
            scopes=scopes,
        )

    async def exchange_code(self, code: str) -> TokenResponse:
        """Exchange authorization code for mock tokens.

        In test mode, we treat the code as a mock access token directly,
        since it contains the character info we need.

        Args:
            code: The authorization code (which is actually a mock access token)

        Returns:
            TokenResponse with the code as both access and refresh token
        """
        return TokenResponse(
            access_token=code,
            refresh_token=f"refresh_{code}",
            expires_in=1200,
            token_type="Bearer",
        )

    async def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        """Refresh mock tokens.

        Args:
            refresh_token: The refresh token

        Returns:
            TokenResponse with same mock token structure
        """
        # Extract original token from refresh_xxx format
        access_token = refresh_token.removeprefix("refresh_")
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=1200,
            token_type="Bearer",
        )


async def provide_mock_sso_service() -> MockEveSSOService:
    """Provide mock SSO service for dependency injection in tests."""
    return MockEveSSOService()


def create_mock_jwt_payload(
    character_id: int,
    character_name: str,
    scopes: list[str] | None = None,
) -> dict:
    """Create a mock JWT payload for testing.

    Args:
        character_id: EVE character ID
        character_name: EVE character name
        scopes: List of ESI scopes (defaults to ["publicData"])

    Returns:
        JWT payload dictionary
    """
    return {
        "sub": f"CHARACTER:EVE:{character_id}",
        "name": character_name,
        "scp": scopes or ["publicData"],
        "iss": "https://login.eveonline.com",
        "aud": ["EVE Online", "test_client_id"],
        "exp": 9999999999,  # Far future
    }


def create_mock_access_token(
    character_id: int,
    character_name: str,
    scopes: list[str] | None = None,
) -> str:
    """Create a mock JWT access token for testing.

    Creates a simple base64-encoded token that MockEveSSOService can decode.
    This is not a real JWT but works for testing purposes.

    Args:
        character_id: EVE character ID
        character_name: EVE character name
        scopes: List of ESI scopes

    Returns:
        Mock JWT token string in format header.payload.signature
    """
    header = base64.urlsafe_b64encode(json.dumps({"alg": "none"}).encode()).decode().rstrip("=")
    payload_data = create_mock_jwt_payload(character_id, character_name, scopes)
    payload = base64.urlsafe_b64encode(json.dumps(payload_data).encode()).decode().rstrip("=")
    return f"{header}.{payload}.mock_signature"
