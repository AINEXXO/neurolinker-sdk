from __future__ import annotations

from typing import Any, Dict

import httpx

from .analyze import AnalyzeResource, AsyncAnalyzeResource
from .jobs import AsyncJobsResource, JobsResource
from .results import AsyncResultsResource, ResultsResource


class ChunkingModule:
    """Chunking module — job submission, analysis, signed-URL results."""

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
        self._analyze = AnalyzeResource(base_url, token, client)
        self._results = ResultsResource(base_url, token, client)

    def analyze(self, bucket_uid: str) -> Dict[str, Any]:
        """POST /v1/chunk/analyze.

        Generates statistics and a distribution plot, returns a `ResultsResponse`
        whose ``result.files`` maps the filenames (`chunking_statistics.json`,
        `chunking_distribution.png`) to short-lived signed URLs.
        """
        return self._analyze.analyze(bucket_uid)

    def results(self, bucket_uid: str) -> Dict[str, bytes]:
        """POST /v1/chunk/results then fetch each signed URL.

        Returns ``{filename: bytes}``. File bytes transit directly between the
        client and the storage backend, not through the API server.
        """
        return self._results.results(bucket_uid)


class AsyncChunkingModule:
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
        self._analyze = AsyncAnalyzeResource(base_url, token, client)
        self._results = AsyncResultsResource(base_url, token, client)

    async def analyze(self, bucket_uid: str) -> Dict[str, Any]:
        return await self._analyze.analyze(bucket_uid)

    async def results(self, bucket_uid: str) -> Dict[str, bytes]:
        return await self._results.results(bucket_uid)
