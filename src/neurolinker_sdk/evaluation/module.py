from __future__ import annotations

import httpx

from .oneshot.module import AsyncOneshotModule, OneshotModule
from .tracking.module import AsyncTrackingModule, TrackingModule


class EvaluationModule:
    """Evaluation module — one-shot batch evaluation (`.oneshot`) and continuous
    tracking of a production RAG (`.tracking`). Mirrors the backend `evaluation`
    module's two sub-areas."""

    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        client: httpx.Client,
        timeout_s: float,
        poll_interval_s: float,
        poll_max_interval_s: float,
    ):
        self.oneshot = OneshotModule(
            base_url=base_url,
            token=token,
            client=client,
            timeout_s=timeout_s,
            poll_interval_s=poll_interval_s,
            poll_max_interval_s=poll_max_interval_s,
        )
        self.tracking = TrackingModule(base_url=base_url, token=token, client=client)


class AsyncEvaluationModule:
    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        client: httpx.AsyncClient,
        timeout_s: float,
        poll_interval_s: float,
        poll_max_interval_s: float,
    ):
        self.oneshot = AsyncOneshotModule(
            base_url=base_url,
            token=token,
            client=client,
            timeout_s=timeout_s,
            poll_interval_s=poll_interval_s,
            poll_max_interval_s=poll_max_interval_s,
        )
        self.tracking = AsyncTrackingModule(base_url=base_url, token=token, client=client)
