from __future__ import annotations

import json

import httpx

from neurolinker_sdk import NeuroLinker
from neurolinker_sdk.config import DEFAULT_BASE_URL
from neurolinker_sdk.embedding import Content, EmbeddingVector

BUCKET_UID = "bkt_00000000-0000-0000-0000-000000000000"
JOB_UID = "job_00000000-0000-0000-0000-000000000000"


def _text_embeddings() -> list[Content]:
    return [
        Content(
            content_type="text",
            inputs=["content"],
            vectors=[
                EmbeddingVector(
                    vector_type="dense",
                    field_name="text_dense_bge",
                    model_name="ainexxo-bge-m3",
                ),
            ],
        )
    ]


def test_wrapper_jobs_get_sync_uses_default_base_url_when_missing() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(
            200,
            json={
                "success": True,
                "job_uid": JOB_UID,
                "status": "completed",
                "bucket_uid": BUCKET_UID,
            },
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            client.embedding.jobs.get(BUCKET_UID, JOB_UID)

    assert captured["url"] == f"{DEFAULT_BASE_URL.rstrip('/')}/v1/embed/jobs/{BUCKET_UID}/{JOB_UID}"


def test_wrapper_jobs_create_sync_uses_default_base_url_when_missing() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "success": True,
                "job_uid": JOB_UID,
                "status": "pending",
                "bucket_uid": BUCKET_UID,
            },
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            client.embedding.jobs.create(
                bucket_uid=BUCKET_UID,
                embeddings=_text_embeddings(),
            )

    assert captured["url"] == f"{DEFAULT_BASE_URL.rstrip('/')}/v1/embed/jobs"
    assert captured["body"]["bucket_uid"] == BUCKET_UID
    assert captured["body"]["embeddings"][0]["content_type"] == "text"


def test_wrapper_list_models_sync_uses_default_base_url() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json={"models": []}, request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            client.embedding.list_models()

    assert captured["url"] == f"{DEFAULT_BASE_URL.rstrip('/')}/v1/embed/models"
