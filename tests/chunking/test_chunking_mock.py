from __future__ import annotations

import json
from typing import List

import httpx
import pytest
from pydantic import BaseModel

from neurolinker_sdk import AsyncNeuroLinker, NeuroLinker, NeuroLinkerConfigError
from neurolinker_sdk.chunking import BlockWindowConfig, SectionGreedyConfig

BUCKET_UID = "bkt_00000000-0000-0000-0000-000000000000"
JOB_UID = "job_00000000-0000-0000-0000-000000000000"


# ---------------------------------------------------------------------------
# create_job
# ---------------------------------------------------------------------------


def test_create_job_with_pydantic_config_sync() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={"success": True, "job_uid": JOB_UID, "status": "pending",
                  "bucket_uid": BUCKET_UID, "message": "enqueued"},
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            resp = client.chunking.jobs.create(
                bucket_uid=BUCKET_UID,
                chunking=SectionGreedyConfig(t_min=100, t_max=512, parse_figures=True),
            )

    assert captured["url"].endswith("/v1/chunk/jobs")
    assert captured["body"]["bucket_uid"] == BUCKET_UID
    assert captured["body"]["chunking"]["method"] == "section_greedy"
    assert captured["body"]["chunking"]["t_min"] == 100
    assert captured["body"]["chunking"]["t_max"] == 512
    assert captured["body"]["chunking"]["parse_figures"] is True
    # exclude_none means None fields are dropped
    assert "model_name" not in captured["body"]["chunking"]
    assert resp["job_uid"] == JOB_UID


def test_create_job_with_dict_sync_validates_discriminator() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={"success": True, "job_uid": JOB_UID, "status": "pending",
                  "bucket_uid": BUCKET_UID},
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            client.chunking.jobs.create(
                bucket_uid=BUCKET_UID,
                chunking={"method": "md_header_level", "chunk_at_level": 2},
            )

    assert captured["body"]["chunking"] == {
        "method": "md_header_level",
        "chunk_at_level": 2,
    }


def test_create_job_rejects_invalid_dict_payload() -> None:
    with NeuroLinker(token="nl_dummy", timeout_s=1.0) as client:
        # Missing method
        with pytest.raises(NeuroLinkerConfigError):
            client.chunking.jobs.create(
                bucket_uid=BUCKET_UID, chunking={"t_max": 512}
            )
        # Unknown method
        with pytest.raises(NeuroLinkerConfigError):
            client.chunking.jobs.create(
                bucket_uid=BUCKET_UID, chunking={"method": "not_real"}
            )
        # Unknown field (extra='forbid')
        with pytest.raises(NeuroLinkerConfigError):
            client.chunking.jobs.create(
                bucket_uid=BUCKET_UID,
                chunking={"method": "section_greedy", "bogus_field": 1},
            )
        # Non-dict non-model
        with pytest.raises(NeuroLinkerConfigError):
            client.chunking.jobs.create(bucket_uid=BUCKET_UID, chunking=42)  # type: ignore[arg-type]


def test_create_job_rejects_unrelated_pydantic_model() -> None:
    class NotAChunkingConfig(BaseModel):
        totally_different: int = 1

    with NeuroLinker(token="nl_dummy", timeout_s=1.0) as client:
        with pytest.raises(NeuroLinkerConfigError):
            client.chunking.jobs.create(
                bucket_uid=BUCKET_UID,
                chunking=NotAChunkingConfig(),
            )


def test_create_job_rejects_empty_bucket_uid() -> None:
    with NeuroLinker(token="nl_dummy", timeout_s=1.0) as client:
        with pytest.raises(NeuroLinkerConfigError):
            client.chunking.jobs.create(
                bucket_uid="", chunking=SectionGreedyConfig()
            )


@pytest.mark.asyncio
async def test_create_job_with_pydantic_config_async() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={"success": True, "job_uid": JOB_UID, "status": "pending",
                  "bucket_uid": BUCKET_UID},
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        async with AsyncNeuroLinker(
            token="nl_dummy", http_client=http_client, timeout_s=1.0
        ) as client:
            await client.chunking.jobs.create(
                bucket_uid=BUCKET_UID,
                chunking=BlockWindowConfig(
                    t_max=400, overlap_blocks=1, overlap_mode="within_budget"
                ),
            )

    assert captured["body"]["chunking"]["method"] == "block_window"
    assert captured["body"]["chunking"]["overlap_mode"] == "within_budget"


# ---------------------------------------------------------------------------
# get_job
# ---------------------------------------------------------------------------


def test_get_job_sync() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        return httpx.Response(
            200,
            json={"job_uid": JOB_UID, "status": "completed", "bucket_uid": BUCKET_UID},
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            resp = client.chunking.jobs.get(BUCKET_UID, JOB_UID)

    assert captured["method"] == "GET"
    assert captured["url"].endswith(f"/v1/chunk/jobs/{BUCKET_UID}/{JOB_UID}")
    assert resp["status"] == "completed"


# ---------------------------------------------------------------------------
# wait_for_job
# ---------------------------------------------------------------------------


def test_wait_for_job_sync_polls_until_terminal() -> None:
    statuses = iter([
        {"job_uid": JOB_UID, "status": "processing"},
        {"job_uid": JOB_UID, "status": "processing"},
        {"job_uid": JOB_UID, "status": "completed", "bucket_uid": BUCKET_UID},
    ])

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=next(statuses), request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(
            token="nl_dummy",
            http_client=http_client,
            timeout_s=5.0,
            poll_interval_s=0.0,
            poll_max_interval_s=0.0,
        ) as client:
            final = client.chunking.jobs.wait(BUCKET_UID, JOB_UID)

    assert final["status"] == "completed"


def test_wait_for_job_sync_tolerates_404_transient() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(404, json={"detail": "job not yet created"}, request=request)
        return httpx.Response(200, json={"status": "completed"}, request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(
            token="nl_dummy",
            http_client=http_client,
            timeout_s=5.0,
            poll_interval_s=0.0,
            poll_max_interval_s=0.0,
        ) as client:
            final = client.chunking.jobs.wait(BUCKET_UID, JOB_UID)

    assert final["status"] == "completed"
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_wait_for_job_async_polls() -> None:
    statuses = iter([
        {"status": "processing"},
        {"status": "completed"},
    ])

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=next(statuses), request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        async with AsyncNeuroLinker(
            token="nl_dummy",
            http_client=http_client,
            timeout_s=5.0,
            poll_interval_s=0.0,
            poll_max_interval_s=0.0,
        ) as client:
            final = await client.chunking.jobs.wait(BUCKET_UID, JOB_UID)

    assert final["status"] == "completed"


# ---------------------------------------------------------------------------
# analyze
# ---------------------------------------------------------------------------


def test_analyze_sync_posts_bucket_uid() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={"success": True, "message": "ok",
                  "result": {"bucket_uid": BUCKET_UID, "success": True}},
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            client.chunking.analyze(BUCKET_UID)

    assert captured["url"].endswith("/v1/chunk/analyze")
    assert captured["body"] == {"bucket_uid": BUCKET_UID}


def test_analyze_rejects_empty_bucket_uid() -> None:
    with NeuroLinker(token="nl_dummy", timeout_s=1.0) as client:
        with pytest.raises(NeuroLinkerConfigError):
            client.chunking.analyze("")


# ---------------------------------------------------------------------------
# results — 2-step signed URL flow
# ---------------------------------------------------------------------------


def test_results_sync_fetches_signed_urls_sequentially() -> None:
    calls: List[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        calls.append(path)
        if path.endswith("/v1/chunk/results"):
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "result": {
                        "bucket_uid": BUCKET_UID,
                        "success": True,
                        "expires_at": "2099-01-01T00:00:00Z",
                        "files": {
                            "chunking.msgpack": "https://storage.googleapis.com/fake/chunking.msgpack?signed=abc",
                        },
                        "missing_files": [],
                        "error": None,
                    },
                },
                request=request,
            )
        if "chunking.msgpack" in str(request.url):
            return httpx.Response(200, content=b"\xa0msgpack-bytes", request=request)
        return httpx.Response(404, request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            out = client.chunking.results(BUCKET_UID)

    assert out == {"chunking.msgpack": b"\xa0msgpack-bytes"}
    # Exactly 1 POST + 1 GET
    assert len(calls) == 2
    assert calls[0].endswith("/v1/chunk/results")


def test_results_sync_empty_files_returns_empty_dict() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "success": True,
                "result": {
                    "bucket_uid": BUCKET_UID,
                    "success": False,
                    "expires_at": None,
                    "files": {},
                    "missing_files": ["chunking.msgpack"],
                    "error": "No output files found for this bucket",
                },
            },
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            out = client.chunking.results(BUCKET_UID)

    assert out == {}


@pytest.mark.asyncio
async def test_results_async_fetches_in_parallel() -> None:
    calls: List[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        calls.append(path)
        if path.endswith("/v1/chunk/results"):
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "result": {
                        "bucket_uid": BUCKET_UID,
                        "success": True,
                        "expires_at": "2099-01-01T00:00:00Z",
                        "files": {
                            f"file_{i}.bin": f"https://storage.googleapis.com/fake/file_{i}?signed={i}"
                            for i in range(3)
                        },
                        "missing_files": [],
                        "error": None,
                    },
                },
                request=request,
            )
        for i in range(3):
            if f"file_{i}" in str(request.url):
                return httpx.Response(200, content=f"content-{i}".encode(), request=request)
        return httpx.Response(404, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        async with AsyncNeuroLinker(
            token="nl_dummy", http_client=http_client, timeout_s=1.0
        ) as client:
            out = await client.chunking.results(BUCKET_UID)

    assert out == {
        "file_0.bin": b"content-0",
        "file_1.bin": b"content-1",
        "file_2.bin": b"content-2",
    }
    # 1 POST + 3 parallel GETs
    assert len(calls) == 4


def test_results_rejects_empty_bucket_uid() -> None:
    with NeuroLinker(token="nl_dummy", timeout_s=1.0) as client:
        with pytest.raises(NeuroLinkerConfigError):
            client.chunking.results("")
