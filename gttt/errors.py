"""Domain and API exceptions."""

from __future__ import annotations


class GTTTError(Exception):
    """Base exception for this project."""


class APIClientError(GTTTError):
    """Base error raised by the API client."""


class APITransportError(APIClientError):
    """Raised when HTTP transport fails or response is not valid JSON."""


class APIResponseError(APIClientError):
    """Raised when API returns code=FAIL."""

    def __init__(self, message: str, payload: dict | None = None) -> None:
        super().__init__(message)
        self.payload = payload or {}


class InvalidBoardError(GTTTError):
    """Raised when a board string cannot be parsed."""


class SearchError(GTTTError):
    """Raised when search cannot provide a legal move."""
