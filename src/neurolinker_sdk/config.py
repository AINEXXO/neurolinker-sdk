from __future__ import annotations

import os
from dataclasses import dataclass

from .errors import NeuroLinkerConfigError

# Default base URL used when NEUROLINKER_BASE_URL is not provided.
# Choose the canonical/public deployment you want as the default.
DEFAULT_BASE_URL = "https://dev.ainexxo.com/neurolinker"


@dataclass(frozen=True)
class NeuroLinkerConfig:
    """
    SDK configuration.

    base_url is optional in the environment: if not provided, DEFAULT_BASE_URL is used.
    token is required.

    base_url should include the deployment path if the API is mounted there,
    e.g. https://dev.ainexxo.com/neurolinker.
    """
    base_url: str = DEFAULT_BASE_URL
    token: str = ""
    timeout_s: float = 30.0

    @staticmethod
    def from_env() -> "NeuroLinkerConfig":
        base_url = os.getenv("NEUROLINKER_BASE_URL", "").strip()
        token = os.getenv("NEUROLINKER_TOKEN", "").strip()

        if not token:
            raise NeuroLinkerConfigError("NEUROLINKER_TOKEN is not set.")

        # If base_url is not set, fall back to DEFAULT_BASE_URL.
        if not base_url:
            base_url = DEFAULT_BASE_URL

        # Normalize to avoid double slashes.
        base_url = base_url.rstrip("/")

        return NeuroLinkerConfig(base_url=base_url, token=token)