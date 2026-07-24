from __future__ import annotations

import httpx

from .buckets import AsyncBucketsResource, BucketsResource


class ManagementModule:
    """Management module — bucket CRUD."""

    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        client: httpx.Client,
    ):
        self.buckets = BucketsResource(base_url, token, client)


class AsyncManagementModule:
    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        client: httpx.AsyncClient,
    ):
        self.buckets = AsyncBucketsResource(base_url, token, client)
