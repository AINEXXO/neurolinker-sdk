from __future__ import annotations

import json
from typing import List

import httpx
import pytest

from neurolinker_sdk import AsyncNeuroLinker, NeuroLinker, NeuroLinkerConfigError
from neurolinker_sdk.embedding import (
    EmbeddingModalities,
    ImageModality,
    ModalityVectors,
    ModelRef,
    TextModality,
    VectorConfig,
)

BUCKET_UID = "bkt_00000000-0000-0000-0000-000000000000"
JOB_UID = "job_00000000-0000-0000-0000-000000000000"


def _text_only_modalities() -> EmbeddingModalities:
    return EmbeddingModalities(
        text=TextModality(
            vectors=ModalityVectors(
                dense=VectorConfig(
                    vector_name="text_dense_bge",
                    model=ModelRef(
                        endpoint="http://embedding-svc/compute_vectors",
                        model_name="bge-m3",
                    ),
                    inputs=["content"],
                ),
            ),
        ),
    )


# ---------------------------------------------------------------------------
# jobs.create
# ---------------------------------------------------------------------------


def test_create_job_with_pydantic_modalities_sync() -> None:
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
            resp = client.embedding.jobs.create(
                bucket_uid=BUCKET_UID,
                modalities=_text_only_modalities(),
            )

    assert captured["url"].endswith("/v1/embed/jobs")
    assert captured["body"]["bucket_uid"] == BUCKET_UID
    text_dense = captured["body"]["modalities"]["text"]["vectors"]["dense"]
    assert text_dense["vector_name"] == "text_dense_bge"
    assert text_dense["model"]["model_name"] == "bge-m3"
    assert text_dense["inputs"] == ["content"]
    # exclude_none means None optional fields are dropped
    assert "sparse" not in captured["body"]["modalities"]["text"]["vectors"]
    assert "image" not in captured["body"]["modalities"]
    assert resp["job_uid"] == JOB_UID


def test_create_job_with_dict_payload_sync() -> None:
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
            client.embedding.jobs.create(
                bucket_uid=BUCKET_UID,
                modalities={
                    "text": {
                        "vectors": {
                            "dense": {
                                "vector_name": "text_dense_bge",
                                "model": {
                                    "endpoint": "http://embedding-svc/compute_vectors",
                                    "model_name": "bge-m3",
                                },
                                "inputs": ["content"],
                            }
                        }
                    }
                },
            )

    dense_body = captured["body"]["modalities"]["text"]["vectors"]["dense"]
    assert dense_body["vector_name"] == "text_dense_bge"


def test_create_job_rejects_invalid_dict_payload() -> None:
    with NeuroLinker(token="nl_dummy", timeout_s=1.0) as client:
        # Reserved vector_name prefix 'item_'
        with pytest.raises(NeuroLinkerConfigError):
            client.embedding.jobs.create(
                bucket_uid=BUCKET_UID,
                modalities={
                    "text": {
                        "vectors": {
                            "dense": {
                                "vector_name": "item_dense",
                                "model": {"endpoint": "http://x", "model_name": "m"},
                            }
                        }
                    }
                },
            )
        # Invalid endpoint (no scheme)
        with pytest.raises(NeuroLinkerConfigError):
            client.embedding.jobs.create(
                bucket_uid=BUCKET_UID,
                modalities={
                    "text": {
                        "vectors": {
                            "dense": {
                                "vector_name": "text_dense",
                                "model": {"endpoint": "embedding-svc", "model_name": "m"},
                            }
                        }
                    }
                },
            )
        # Unknown top-level modality (extra='forbid')
        with pytest.raises(NeuroLinkerConfigError):
            client.embedding.jobs.create(
                bucket_uid=BUCKET_UID,
                modalities={"audio": {"vectors": {"dense": None}}},
            )
        # Non-dict non-model
        with pytest.raises(NeuroLinkerConfigError):
            client.embedding.jobs.create(bucket_uid=BUCKET_UID, modalities=42)  # type: ignore[arg-type]


def test_create_job_rejects_empty_bucket_uid() -> None:
    with NeuroLinker(token="nl_dummy", timeout_s=1.0) as client:
        with pytest.raises(NeuroLinkerConfigError):
            client.embedding.jobs.create(
                bucket_uid="", modalities=_text_only_modalities()
            )


@pytest.mark.asyncio
async def test_create_job_with_multi_modal_async() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={"success": True, "job_uid": JOB_UID, "status": "pending",
                  "bucket_uid": BUCKET_UID},
            request=request,
        )

    modalities = EmbeddingModalities(
        text=TextModality(
            vectors=ModalityVectors(
                dense=VectorConfig(
                    vector_name="text_dense_bge",
                    model=ModelRef(
                        endpoint="http://embedding-svc/compute_vectors",
                        model_name="bge-m3",
                    ),
                    inputs=["content"],
                ),
                sparse=VectorConfig(
                    vector_name="text_sparse_splade",
                    model=ModelRef(
                        endpoint="http://embedding-svc/compute_vectors",
                        model_name="splade",
                    ),
                    inputs=["content"],
                ),
            ),
        ),
        image=ImageModality(
            vectors=ModalityVectors(
                dense=VectorConfig(
                    vector_name="image_dense_voyage",
                    model=ModelRef(
                        endpoint="https://api.voyageai.com/v1/multimodalembeddings",
                        model_name="voyage-multimodal-3",
                        secret_id="neurolinker__user_42__voyage_key",
                    ),
                    inputs=["image_base64"],
                ),
            ),
        ),
    )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        async with AsyncNeuroLinker(
            token="nl_dummy", http_client=http_client, timeout_s=1.0
        ) as client:
            await client.embedding.jobs.create(
                bucket_uid=BUCKET_UID, modalities=modalities
            )

    body_modalities = captured["body"]["modalities"]
    assert set(body_modalities.keys()) == {"text", "image"}
    assert body_modalities["text"]["vectors"]["dense"]["vector_name"] == "text_dense_bge"
    assert body_modalities["text"]["vectors"]["sparse"]["vector_name"] == "text_sparse_splade"
    assert body_modalities["image"]["vectors"]["dense"]["model"]["secret_id"] == \
        "neurolinker__user_42__voyage_key"
    # api_key is None → dropped
    assert "api_key" not in body_modalities["image"]["vectors"]["dense"]["model"]


# ---------------------------------------------------------------------------
# jobs.get
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
            resp = client.embedding.jobs.get(JOB_UID)

    assert captured["method"] == "GET"
    assert captured["url"].endswith(f"/v1/embed/jobs/{JOB_UID}")
    assert resp["status"] == "completed"


def test_get_job_rejects_empty_job_uid() -> None:
    with NeuroLinker(token="nl_dummy", timeout_s=1.0) as client:
        with pytest.raises(NeuroLinkerConfigError):
            client.embedding.jobs.get("")


# ---------------------------------------------------------------------------
# jobs.wait
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
            final = client.embedding.jobs.wait(JOB_UID)

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
            final = client.embedding.jobs.wait(JOB_UID)

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
            final = await client.embedding.jobs.wait(JOB_UID)

    assert final["status"] == "completed"


# ---------------------------------------------------------------------------
# list_models
# ---------------------------------------------------------------------------


def test_list_models_sync() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        return httpx.Response(
            200,
            json={
                "models": [
                    {"name": "bge-m3", "endpoint": "http://embedding-svc/compute_vectors",
                     "vector_types": ["dense", "sparse"]},
                    {"name": "splade", "endpoint": "http://embedding-svc/compute_vectors",
                     "vector_types": ["sparse"]},
                ]
            },
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            resp = client.embedding.list_models()

    assert captured["method"] == "GET"
    assert captured["url"].endswith("/v1/embed/models")
    assert len(resp["models"]) == 2
    assert resp["models"][0]["name"] == "bge-m3"


@pytest.mark.asyncio
async def test_list_models_async() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json={"models": []}, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        async with AsyncNeuroLinker(
            token="nl_dummy", http_client=http_client, timeout_s=1.0
        ) as client:
            resp = await client.embedding.list_models()

    assert captured["url"].endswith("/v1/embed/models")
    assert resp == {"models": []}


# ---------------------------------------------------------------------------
# results — 2-step signed URL flow
# ---------------------------------------------------------------------------


def test_results_sync_fetches_signed_urls_sequentially() -> None:
    calls: List[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        calls.append(path)
        if path.endswith("/v1/embed/results"):
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "result": {
                        "bucket_uid": BUCKET_UID,
                        "success": True,
                        "expires_at": "2099-01-01T00:00:00Z",
                        "files": {
                            "embeddings.msgpack": "https://storage.googleapis.com/fake/embeddings.msgpack?signed=abc",
                        },
                        "missing_files": [],
                        "error": None,
                    },
                },
                request=request,
            )
        if "embeddings.msgpack" in str(request.url):
            return httpx.Response(200, content=b"\xa0msgpack-embedding-bytes", request=request)
        return httpx.Response(404, request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            out = client.embedding.results(BUCKET_UID)

    assert out == {"embeddings.msgpack": b"\xa0msgpack-embedding-bytes"}
    # Exactly 1 POST + 1 GET
    assert len(calls) == 2
    assert calls[0].endswith("/v1/embed/results")


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
                    "missing_files": ["embeddings.msgpack"],
                    "error": "No output files found for this bucket",
                },
            },
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            out = client.embedding.results(BUCKET_UID)

    assert out == {}


@pytest.mark.asyncio
async def test_results_async_fetches_in_parallel() -> None:
    calls: List[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        calls.append(path)
        if path.endswith("/v1/embed/results"):
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
            out = await client.embedding.results(BUCKET_UID)

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
            client.embedding.results("")
