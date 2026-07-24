from __future__ import annotations

import json

import httpx
import pytest

from neurolinker_sdk import AsyncNeuroLinker, NeuroLinker, NeuroLinkerConfigError

TRACK_UID = "c6883578-1a2b-4c3d-8e9f-0a1b2c3d4e5f"
TRACE_ID = "0af7651916cd43dd8448eb211c80319c"


# ---------------------------------------------------------------------------
# tracks.create — POST /v1/eval/tracks
# ---------------------------------------------------------------------------


def test_create_track_sync() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["body"] = request.content.decode()
        return httpx.Response(
            200, json={"track_uid": TRACK_UID, "name": "prod-rag", "active": True}, request=request
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            resp = client.evaluation.tracking.tracks.create(name="prod-rag")

    assert captured["method"] == "POST"
    assert captured["url"].endswith("/v1/eval/tracks")
    assert json.loads(captured["body"]) == {"name": "prod-rag"}
    assert resp["track_uid"] == TRACK_UID


def test_list_tracks_sync() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        return httpx.Response(
            200, json={"tracks": [{"track_uid": TRACK_UID, "name": "prod-rag", "active": True}]},
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            resp = client.evaluation.tracking.tracks.list()

    assert captured["method"] == "GET"
    assert captured["url"].endswith("/v1/eval/tracks")
    assert resp["tracks"][0]["track_uid"] == TRACK_UID


def test_set_active_sync() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["body"] = request.content.decode()
        return httpx.Response(
            200, json={"track_uid": TRACK_UID, "name": "prod-rag", "active": False}, request=request
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            resp = client.evaluation.tracking.tracks.set_active(TRACK_UID, active=False)

    assert captured["method"] == "PATCH"
    assert captured["url"].endswith(f"/v1/eval/tracks/{TRACK_UID}")
    assert json.loads(captured["body"]) == {"active": False}
    assert resp["active"] is False


# ---------------------------------------------------------------------------
# dashboard reads — queries / query
# ---------------------------------------------------------------------------


def test_queries_sync() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["limit"] = request.url.params.get("limit")
        return httpx.Response(
            200,
            json={"track_uid": TRACK_UID, "queries": [
                {"trace_id": TRACE_ID, "user_input": "Q", "response": "A",
                 "metrics": {"faithfulness": 0.9}},
            ]},
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            resp = client.evaluation.tracking.queries(TRACK_UID, limit=50)

    assert captured["url"].endswith(f"/v1/eval/tracks/{TRACK_UID}/queries?limit=50")
    assert captured["limit"] == "50"
    assert resp["queries"][0]["trace_id"] == TRACE_ID


def test_query_sync() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(
            200,
            json={"track_uid": TRACK_UID, "trace_id": TRACE_ID, "user_input": "Q",
                  "response": "A", "retrieved_contexts": ["ctx"], "metrics": {}},
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            resp = client.evaluation.tracking.query(TRACK_UID, TRACE_ID)

    assert captured["url"].endswith(f"/v1/eval/tracks/{TRACK_UID}/queries/{TRACE_ID}")
    assert resp["retrieved_contexts"] == ["ctx"]


# ---------------------------------------------------------------------------
# validation — client-side guards on user-supplied input
# ---------------------------------------------------------------------------


def test_validation_sync() -> None:
    with NeuroLinker(token="nl_dummy", timeout_s=1.0) as client:
        with pytest.raises(NeuroLinkerConfigError):
            client.evaluation.tracking.tracks.create(name="")
        with pytest.raises(NeuroLinkerConfigError):
            client.evaluation.tracking.tracks.set_active("", active=True)
        with pytest.raises(NeuroLinkerConfigError):
            client.evaluation.tracking.queries("")
        with pytest.raises(NeuroLinkerConfigError):
            client.evaluation.tracking.query(TRACK_UID, "")


# ---------------------------------------------------------------------------
# async parity — a representative create + queries
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_track_async() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"track_uid": TRACK_UID, "name": "p"}, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        async with AsyncNeuroLinker(
            token="nl_dummy", http_client=http_client, timeout_s=1.0
        ) as client:
            resp = await client.evaluation.tracking.tracks.create(name="prod-rag")

    assert resp["track_uid"] == TRACK_UID


@pytest.mark.asyncio
async def test_queries_async() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json={"track_uid": TRACK_UID, "queries": []}, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        async with AsyncNeuroLinker(
            token="nl_dummy", http_client=http_client, timeout_s=1.0
        ) as client:
            resp = await client.evaluation.tracking.queries(TRACK_UID, limit=10)

    assert captured["url"].endswith(f"/v1/eval/tracks/{TRACK_UID}/queries?limit=10")
    assert resp["queries"] == []
