from __future__ import annotations

import json

import httpx
import pytest

from neurolinker_sdk import AsyncNeuroLinker, NeuroLinker, NeuroLinkerConfigError

EVAL_UID = "a1645cc1-230a-4ec3-9b3a-c815592fb1ac"
_JSONL = b'{"user_input": "Q", "response": "R"}\n'


# ---------------------------------------------------------------------------
# create — multipart JSONL upload
# ---------------------------------------------------------------------------


def test_create_uploads_jsonl_sync() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["content"] = request.content
        return httpx.Response(
            200,
            json={"eval_uid": EVAL_UID, "status": "pending", "message": "enqueued"},
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            resp = client.evaluation.oneshot.jobs.create(dataset=("demo.jsonl", _JSONL))

    assert captured["url"].endswith("/v1/eval/oneshot/jobs")
    # The multipart body carries the filename and the JSONL bytes.
    body = captured["content"].decode("utf-8", errors="replace")
    assert "demo.jsonl" in body
    assert '"user_input": "Q"' in body
    assert resp["eval_uid"] == EVAL_UID


@pytest.mark.asyncio
async def test_create_uploads_jsonl_async() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["content"] = request.content
        return httpx.Response(
            200, json={"eval_uid": EVAL_UID, "status": "pending"}, request=request
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        async with AsyncNeuroLinker(
            token="nl_dummy", http_client=http_client, timeout_s=1.0
        ) as client:
            resp = await client.evaluation.oneshot.jobs.create(dataset=("demo.jsonl", _JSONL))

    assert captured["url"].endswith("/v1/eval/oneshot/jobs")
    assert "demo.jsonl" in captured["content"].decode("utf-8", errors="replace")
    assert resp["eval_uid"] == EVAL_UID


def test_create_rejects_invalid_dataset() -> None:
    with NeuroLinker(token="nl_dummy", timeout_s=1.0) as client:
        with pytest.raises(NeuroLinkerConfigError):  # not a (filename, bytes) tuple
            client.evaluation.oneshot.jobs.create(dataset="data.jsonl")  # type: ignore[arg-type]
        with pytest.raises(NeuroLinkerConfigError):  # wrong extension
            client.evaluation.oneshot.jobs.create(dataset=("data.csv", _JSONL))
        with pytest.raises(NeuroLinkerConfigError):  # empty content
            client.evaluation.oneshot.jobs.create(dataset=("data.jsonl", b""))


# ---------------------------------------------------------------------------
# get — status
# ---------------------------------------------------------------------------


def test_get_status_sync() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        return httpx.Response(
            200,
            json={"eval_uid": EVAL_UID, "status": "completed", "rows_evaluated": 6},
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            resp = client.evaluation.oneshot.jobs.get(EVAL_UID)

    assert captured["method"] == "GET"
    assert captured["url"].endswith(f"/v1/eval/oneshot/jobs/{EVAL_UID}")
    assert resp["status"] == "completed"


def test_get_rejects_empty_eval_uid() -> None:
    with NeuroLinker(token="nl_dummy", timeout_s=1.0) as client:
        with pytest.raises(NeuroLinkerConfigError):
            client.evaluation.oneshot.jobs.get("")


# ---------------------------------------------------------------------------
# wait — polls until terminal (completed/failed); pending/processing do not satisfy
# ---------------------------------------------------------------------------


def test_wait_polls_until_completed_sync() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        status = "completed" if calls["n"] >= 2 else "processing"  # not terminal first
        return httpx.Response(200, json={"eval_uid": EVAL_UID, "status": status}, request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=5.0) as client:
            final = client.evaluation.oneshot.jobs.wait(
                EVAL_UID, poll_interval_s=0.01, poll_max_interval_s=0.01
            )

    assert final["status"] == "completed"
    assert calls["n"] >= 2  # it actually polled past the non-terminal "processing"


# ---------------------------------------------------------------------------
# results — 2-step signed-URL flow, returns the parsed result.json
# ---------------------------------------------------------------------------

_RESULT_JSON = {
    "eval_uid": EVAL_UID,
    "rows": [{"row_id": 0, "metrics": {"faithfulness": 0.9}}],
    "summary": {"faithfulness": {"mean": 0.9, "count": 1}},
}


def test_results_two_step_sync() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        calls.append(path)
        if path.endswith("/v1/eval/oneshot/results"):
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "message": "ok",
                    "result": {
                        "eval_uid": EVAL_UID,
                        "success": True,
                        "expires_at": "2099-01-01T00:00:00Z",
                        "files": {
                            "result.json": "https://storage.googleapis.com/fake/result.json?signed=abc"
                        },
                    },
                },
                request=request,
            )
        if "result.json" in str(request.url):
            return httpx.Response(200, content=json.dumps(_RESULT_JSON).encode(), request=request)
        return httpx.Response(404, request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            out = client.evaluation.oneshot.results(EVAL_UID)

    assert out == _RESULT_JSON
    assert len(calls) == 2  # one POST /results + one GET of the signed URL
    assert calls[0].endswith("/v1/eval/oneshot/results")


def test_results_not_ready_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "success": False,
                "message": "Result not yet available",
                "result": {
                    "eval_uid": EVAL_UID,
                    "success": False,
                    "files": {},
                    "missing_files": ["result.json"],
                    "error": "result not yet available",
                },
            },
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            with pytest.raises(NeuroLinkerConfigError):
                client.evaluation.oneshot.results(EVAL_UID)


def test_results_rejects_empty_eval_uid() -> None:
    with NeuroLinker(token="nl_dummy", timeout_s=1.0) as client:
        with pytest.raises(NeuroLinkerConfigError):
            client.evaluation.oneshot.results("")


@pytest.mark.asyncio
async def test_results_two_step_async() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/v1/eval/oneshot/results"):
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "result": {
                        "eval_uid": EVAL_UID,
                        "success": True,
                        "files": {"result.json": "https://fake/result.json?signed=abc"},
                    },
                },
                request=request,
            )
        return httpx.Response(200, content=json.dumps(_RESULT_JSON).encode(), request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        async with AsyncNeuroLinker(
            token="nl_dummy", http_client=http_client, timeout_s=1.0
        ) as client:
            out = await client.evaluation.oneshot.results(EVAL_UID)

    assert out == _RESULT_JSON
