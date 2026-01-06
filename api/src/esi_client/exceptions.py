"""Custom exceptions for ESI client errors."""

from __future__ import annotations


class ESIError(Exception):
    """Base exception for ESI API errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ESINotFoundError(ESIError):
    """Raised when ESI returns 404 Not Found."""

    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message, status_code=404)


class ESIRateLimitError(ESIError):
    """Raised when ESI returns 429 Too Many Requests."""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int | None = None) -> None:
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class ESIServerError(ESIError):
    """Raised when ESI returns 5xx Server Error."""

    def __init__(self, message: str = "ESI server error", status_code: int = 500) -> None:
        super().__init__(message, status_code=status_code)
