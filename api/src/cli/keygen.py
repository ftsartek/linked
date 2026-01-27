"""Standalone key generation commands.

These commands do not require application configuration and can be
run before initial setup to generate required secrets.

Usage:
    linked generate-token-key    # Generate TOKEN_ENCRYPTION_KEY
    linked generate-secret       # Generate CSRF_SECRET or similar
"""

from __future__ import annotations

import secrets

import asyncclick as click
from cryptography.fernet import Fernet


@click.command("generate-token-key")
def generate_token_key() -> None:
    """Generate a Fernet key for TOKEN_ENCRYPTION_KEY.

    This key is used to encrypt refresh tokens stored in the database.
    The key must remain consistent across application restarts, otherwise
    existing encrypted tokens will become unreadable.

    Example:
        export TOKEN_ENCRYPTION_KEY=$(linked generate-token-key)
    """
    key = Fernet.generate_key().decode()
    click.echo(key)


@click.command("generate-secret")
@click.option(
    "--length",
    "-l",
    default=32,
    type=int,
    help="Length of the secret in bytes (default: 32)",
)
def generate_secret(length: int) -> None:
    """Generate a random secret for CSRF_SECRET or similar.

    Outputs a URL-safe base64-encoded random string.

    Example:
        export CSRF_SECRET=$(linked generate-secret)
        export CSRF_SECRET=$(linked generate-secret --length 64)
    """
    secret = secrets.token_urlsafe(length)
    click.echo(secret)
