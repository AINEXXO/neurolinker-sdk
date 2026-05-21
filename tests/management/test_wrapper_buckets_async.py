from __future__ import annotations

import json

import httpx
import pytest

from neurolinker_sdk import AsyncNeuroLinker
from neurolinker_sdk.config import DEFAULT_BASE_URL

BUCKET_UID = "bkt_00000000-0000-0000-0000-000000000000"


@pytest.mark.asyncio
async def test_wrapper_buckets_create_async_uses_default_base_url_when_missing() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            201,
            json={"bucket_uid": BUCKET_UID, "name": "KB"},
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        async with AsyncNeuroLinker(
            token="nl_dummy", http_client=http_client, timeout_s=1.0
        ) as client:
            await client.management.buckets.create(name="KB")

    assert captured["url"] == f"{DEFAULT_BASE_URL.rstrip('/')}/v1/management/buckets"
    assert captured["body"] == {"name": "KB"}


@pytest.mark.asyncio
async def test_wrapper_buckets_get_async_uses_default_base_url_when_missing() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(
            200,
            json={"bucket_uid": BUCKET_UID, "name": "KB", "sources": []},
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        async with AsyncNeuroLinker(
            token="nl_dummy", http_client=http_client, timeout_s=1.0
        ) as client:
            await client.management.buckets.get(BUCKET_UID)

    assert (
        captured["url"]
        == f"{DEFAULT_BASE_URL.rstrip('/')}/v1/management/buckets/{BUCKET_UID}"
    )
