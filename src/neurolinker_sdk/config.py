from __future__ import annotations

import os
from dataclasses import dataclass

from .errors import NeuroLinkerConfigError


@dataclass(frozen=True)
class NeuroLinkerConfig:
    """
    SDK configuration.

    base_url should include the deployment path if the API is mounted there,
    e.g. https://dev.ainexxo.com/neurolinker (as in your case).
    """
    base_url: str
    token: str
    timeout_s: float = 30.0

    @staticmethod
    def from_env() -> "NeuroLinkerConfig":
        base_url = os.getenv("NEUROLINKER_BASE_URL", "").strip()
        token = os.getenv("NEUROLINKER_TOKEN", "").strip()

        if not base_url:
            raise NeuroLinkerConfigError("NEUROLINKER_BASE_URL is not set.") #TODO: il controllo per il token ci sta ma non dobbiamo forzare il base_url,no ?
        if not token:
            raise NeuroLinkerConfigError("NEUROLINKER_TOKEN is not set.")

        # Normalize to avoid double slashes.
        base_url = base_url.rstrip("/")

        return NeuroLinkerConfig(base_url=base_url, token=token)
