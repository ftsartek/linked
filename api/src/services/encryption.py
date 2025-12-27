from __future__ import annotations

from cryptography.fernet import Fernet

from config import get_settings


class EncryptionService:
    """Service for encrypting and decrypting sensitive data using Fernet symmetric encryption."""

    def __init__(self, key: str | bytes | None = None) -> None:
        if key is None:
            key = get_settings().token_encryption_key
        if isinstance(key, str):
            key = key.encode()
        self._fernet = Fernet(key)

    def encrypt(self, plaintext: str) -> bytes:
        """Encrypt a plaintext string and return the ciphertext as bytes."""
        return self._fernet.encrypt(plaintext.encode())

    def decrypt(self, ciphertext: bytes) -> str:
        """Decrypt ciphertext bytes and return the plaintext string."""
        return self._fernet.decrypt(ciphertext).decode()


_encryption_service: EncryptionService | None = None


def get_encryption_service() -> EncryptionService:
    """Get a singleton encryption service instance."""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service
