from __future__ import annotations

import httpx

from .collections import AsyncCollectionsResource, CollectionsResource
from .jobs import AsyncJobsResource, JobsResource


class VectorStoreModule:
    """Vector Store module — collection creation and async vector-load jobs."""

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
        self.collections = CollectionsResource(base_url, token, client)
        self.jobs = JobsResource(
            base_url,
            token,
            client,
            timeout_s=timeout_s,
            poll_interval_s=poll_interval_s,
            poll_max_interval_s=poll_max_interval_s,
        )


class AsyncVectorStoreModule:
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
        self.collections = AsyncCollectionsResource(base_url, token, client)
        self.jobs = AsyncJobsResource(
            base_url,
            token,
            client,
            timeout_s=timeout_s,
            poll_interval_s=poll_interval_s,
            poll_max_interval_s=poll_max_interval_s,
        )
