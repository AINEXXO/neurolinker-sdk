from __future__ import annotations

import os
from dataclasses import dataclass

from .errors import NeuroLinkerConfigError

# Canonical/public NeuroLinker deployment.
DEFAULT_BASE_URL = os.getenv("NEUROLINKER_BASE_URL", "https://neurolinker.api.ainexxo.com")
DEFAULT_TIMEOUT_S = 600.0
DEFAULT_POLL_INTERVAL_S = 2.0
DEFAULT_POLL_MAX_INTERVAL_S = 10.0


@dataclass(frozen=True)
class NeuroLinkerConfig:
    """
    SDK configuration.

    token is required.
    base_url is optional and defaults to the canonical public deployment.
    timeout/poll values are used by request completion helpers.
    """

    base_url: str = DEFAULT_BASE_URL
    token: str = ""
    timeout_s: float = DEFAULT_TIMEOUT_S
    poll_interval_s: float = DEFAULT_POLL_INTERVAL_S
    poll_max_interval_s: float = DEFAULT_POLL_MAX_INTERVAL_S

    @staticmethod
    def from_env() -> NeuroLinkerConfig:
        base_url = os.getenv("NEUROLINKER_BASE_URL", "").strip()
        token = os.getenv("NEUROLINKER_API_KEY", "").strip()
        timeout_s = float(os.getenv("NEUROLINKER_E2E_TIMEOUT_S", str(DEFAULT_TIMEOUT_S)))
        poll_interval_s = float(
            os.getenv("NEUROLINKER_E2E_POLL_INTERVAL_S", str(DEFAULT_POLL_INTERVAL_S))
        )
        poll_max_interval_s = float(
            os.getenv("NEUROLINKER_E2E_POLL_MAX_INTERVAL_S", str(DEFAULT_POLL_MAX_INTERVAL_S))
        )

        if not token:
            raise NeuroLinkerConfigError("NEUROLINKER_API_KEY is not set.")

        if not base_url:
            base_url = DEFAULT_BASE_URL

        base_url = base_url.rstrip("/")

        return NeuroLinkerConfig(
            base_url=base_url,
            token=token,
            timeout_s=timeout_s,
            poll_interval_s=poll_interval_s,
            poll_max_interval_s=poll_max_interval_s,
        )
