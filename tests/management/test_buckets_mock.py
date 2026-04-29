from __future__ import annotations

import json

import httpx
import pytest

from neurolinker_sdk import AsyncNeuroLinker, NeuroLinker, NeuroLinkerConfigError

BUCKET_UID = "bkt_00000000-0000-0000-0000-000000000000"
REQUEST_UID = "req_00000000-0000-0000-0000-000000000000"


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


def test_buckets_create_sync() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            201,
            json={"bucket_uid": BUCKET_UID, "name": "AI Papers Q1"},
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            resp = client.management.buckets.create(name="AI Papers Q1")

    assert captured["method"] == "POST"
    assert captured["url"].endswith("/v1/management/buckets")
    assert captured["body"] == {"name": "AI Papers Q1"}
    assert resp["bucket_uid"] == BUCKET_UID


@pytest.mark.asyncio
async def test_buckets_create_async() -> None:
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
            resp = await client.management.buckets.create(name="KB")

    assert captured["url"].endswith("/v1/management/buckets")
    assert captured["body"] == {"name": "KB"}
    assert resp["bucket_uid"] == BUCKET_UID


def test_buckets_create_rejects_empty_name() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("HTTP call must not happen for client-side validation")

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            with pytest.raises(NeuroLinkerConfigError):
                client.management.buckets.create(name="")


# ---------------------------------------------------------------------------
# add_sources
# ---------------------------------------------------------------------------


def test_buckets_add_sources_sync_returns_none_on_204() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(204, request=request)

    sources = [
        {"request_uid": REQUEST_UID, "doc_uids": ["doc_1", "doc_3"]},
        {"request_uid": "req_two", "doc_uids": None},
    ]

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            ret = client.management.buckets.add_sources(BUCKET_UID, sources=sources)

    assert ret is None
    assert captured["method"] == "POST"
    assert captured["url"].endswith(f"/v1/management/buckets/{BUCKET_UID}/sources")
    assert captured["body"] == {"sources": sources}


def test_buckets_add_sources_rejects_empty_list() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("HTTP call must not happen for client-side validation")

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            with pytest.raises(NeuroLinkerConfigError):
                client.management.buckets.add_sources(BUCKET_UID, sources=[])


def test_buckets_add_sources_rejects_missing_request_uid() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("HTTP call must not happen for client-side validation")

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            with pytest.raises(NeuroLinkerConfigError):
                client.management.buckets.add_sources(
                    BUCKET_UID, sources=[{"doc_uids": ["d"]}]
                )


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


def test_buckets_list_sync() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        return httpx.Response(
            200,
            json={"buckets": [{"bucket_uid": BUCKET_UID, "name": "KB", "sources_count": 1}]},
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            resp = client.management.buckets.list()

    assert captured["method"] == "GET"
    assert captured["url"].endswith("/v1/management/buckets")
    assert resp["buckets"][0]["bucket_uid"] == BUCKET_UID


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------


def test_buckets_get_sync() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(
            200,
            json={
                "bucket_uid": BUCKET_UID,
                "name": "KB",
                "user_uid": "usr_1",
                "created_at": "2026-04-24T00:00:00Z",
                "sources": [],
            },
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            resp = client.management.buckets.get(BUCKET_UID)

    assert captured["url"].endswith(f"/v1/management/buckets/{BUCKET_UID}")
    assert resp["bucket_uid"] == BUCKET_UID


def test_buckets_get_rejects_empty_uid() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("HTTP call must not happen for client-side validation")

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            with pytest.raises(NeuroLinkerConfigError):
                client.management.buckets.get("")


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


def test_buckets_delete_sync_returns_none_on_204() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        return httpx.Response(204, request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            ret = client.management.buckets.delete(BUCKET_UID)

    assert ret is None
    assert captured["method"] == "DELETE"
    assert captured["url"].endswith(f"/v1/management/buckets/{BUCKET_UID}")


@pytest.mark.asyncio
async def test_buckets_delete_async_returns_none_on_204() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(204, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        async with AsyncNeuroLinker(
            token="nl_dummy", http_client=http_client, timeout_s=1.0
        ) as client:
            ret = await client.management.buckets.delete(BUCKET_UID)

    assert ret is None
