from typing import Any


class EWeLinkError(Exception):
    """Base exception for all eWeLink errors."""


class EWeLinkAuthError(EWeLinkError):
    """Authentication or authorization failure."""


class EWeLinkAPIError(EWeLinkError):
    """API returned a non-zero error code."""

    def __init__(self, error: int, msg: str | None = None, data: dict[str, Any] | None = None):
        self.error = error
        self.msg = msg
        self.data = data or {}
        super().__init__(f"API error {error}: {msg}")