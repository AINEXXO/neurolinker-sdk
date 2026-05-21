from __future__ import annotations

import json

import httpx

from neurolinker_sdk import NeuroLinker
from neurolinker_sdk.config import DEFAULT_BASE_URL

BUCKET_UID = "bkt_00000000-0000-0000-0000-000000000000"


def test_wrapper_buckets_create_sync_uses_default_base_url_when_missing() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            201,
            json={"bucket_uid": BUCKET_UID, "name": "KB"},
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            client.management.buckets.create(name="KB")

    assert captured["url"] == f"{DEFAULT_BASE_URL.rstrip('/')}/v1/management/buckets"
    assert captured["body"] == {"name": "KB"}


def test_wrapper_buckets_get_sync_uses_default_base_url_when_missing() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(
            200,
            json={"bucket_uid": BUCKET_UID, "name": "KB", "sources": []},
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            client.management.buckets.get(BUCKET_UID)

    assert (
        captured["url"]
        == f"{DEFAULT_BASE_URL.rstrip('/')}/v1/management/buckets/{BUCKET_UID}"
    )
