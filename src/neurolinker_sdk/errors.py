from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


class NeuroLinkerConfigError(RuntimeError):
    """Raised when the SDK is misconfigured (missing base URL, missing token, invalid values)."""


@dataclass
class NeuroLinkerAPIError(RuntimeError):
    """
    Raised for non-2xx responses from the NeuroLinker API.

    We keep both raw response text and optional JSON payload for debugging.
    """

    status_code: int
    method: str
    url: str
    response_text: str
    response_json: Optional[object] = None

    def __str__(self) -> str:
        return (
            f"NeuroLinker API request failed: {self.status_code} {self.method} {self.url}\n"
            f"Response: {self.response_text[:2000]}"
        )
