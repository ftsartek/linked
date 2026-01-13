"""Mock token utilities for testing.

Provides functions to create mock JWT tokens that MockEveSSOService can decode.
"""

from __future__ import annotations

import base64
import json

from tests.factories.static_data import (
    TEST_CHARACTER_ID,
    TEST_CHARACTER_NAME,
)


def create_mock_jwt_payload(
    character_id: int = TEST_CHARACTER_ID,
    character_name: str = TEST_CHARACTER_NAME,
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
    character_id: int = TEST_CHARACTER_ID,
    character_name: str = TEST_CHARACTER_NAME,
    scopes: list[str] | None = None,
) -> str:
    """Create a mock JWT access token.

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
