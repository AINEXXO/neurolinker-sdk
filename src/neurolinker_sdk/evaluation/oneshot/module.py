from __future__ import annotations

from typing import Any, Dict

import httpx

from .jobs import AsyncJobsResource, JobsResource
from .results import AsyncResultsResource, ResultsResource


class OneshotModule:
    """One-shot evaluation — JSONL job submission, polling, result.json fetch."""

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
        self.jobs = JobsResource(
            base_url,
            token,
            client,
            timeout_s=timeout_s,
            poll_interval_s=poll_interval_s,
            poll_max_interval_s=poll_max_interval_s,
        )
        self._results = ResultsResource(base_url, token, client)

    def results(self, eval_uid: str) -> Dict[str, Any]:
        """POST /v1/eval/oneshot/results then download the signed ``result.json``.

        Returns the parsed evaluation output (``{eval_uid, rows, summary}``). The
        file bytes transit directly between the client and storage, not through
        the API server.
        """
        return self._results.results(eval_uid)


class AsyncOneshotModule:
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
        self.jobs = AsyncJobsResource(
            base_url,
            token,
            client,
            timeout_s=timeout_s,
            poll_interval_s=poll_interval_s,
            poll_max_interval_s=poll_max_interval_s,
        )
        self._results = AsyncResultsResource(base_url, token, client)

    async def results(self, eval_uid: str) -> Dict[str, Any]:
        return await self._results.results(eval_uid)
