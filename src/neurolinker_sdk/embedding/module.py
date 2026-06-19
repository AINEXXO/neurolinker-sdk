from __future__ import annotations

from typing import Any, Dict

import httpx

from .jobs import AsyncJobsResource, JobsResource
from .models_api import AsyncModelsResource, ModelsResource
from .results import AsyncResultsResource, ResultsResource


class EmbeddingModule:
    """Embedding module — job submission, model listing, signed-URL results."""

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
        self._models = ModelsResource(base_url, token, client)
        self._results = ResultsResource(base_url, token, client)

    def list_models(self) -> Dict[str, Any]:
        """GET /v1/embed/models — list internal embedding models."""
        return self._models.list()

    def results(self, bucket_uid: str) -> Dict[str, bytes]:
        """POST /v1/embed/results then fetch each signed URL.

        Returns ``{filename: bytes}``. File bytes transit directly between the
        client and the storage backend, not through the API server.
        """
        return self._results.results(bucket_uid)


class AsyncEmbeddingModule:
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
        self._models = AsyncModelsResource(base_url, token, client)
        self._results = AsyncResultsResource(base_url, token, client)

    async def list_models(self) -> Dict[str, Any]:
        return await self._models.list()

    async def results(self, bucket_uid: str) -> Dict[str, bytes]:
        return await self._results.results(bucket_uid)
