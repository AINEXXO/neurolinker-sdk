from __future__ import annotations

import json

import httpx

from neurolinker_sdk import NeuroLinker
from neurolinker_sdk.config import DEFAULT_BASE_URL
from neurolinker_sdk.embedding import (
    EmbeddingModalities,
    ModalityVectors,
    ModelRef,
    TextModality,
    VectorConfig,
)

BUCKET_UID = "bkt_00000000-0000-0000-0000-000000000000"
JOB_UID = "job_00000000-0000-0000-0000-000000000000"


def _text_modalities() -> EmbeddingModalities:
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


def test_wrapper_jobs_get_sync_uses_default_base_url_when_missing() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(
            200,
            json={"success": True, "job_uid": JOB_UID, "status": "completed",
                  "bucket_uid": BUCKET_UID},
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            client.embedding.jobs.get(JOB_UID)

    assert captured["url"] == f"{DEFAULT_BASE_URL.rstrip('/')}/v1/embed/jobs/{JOB_UID}"


def test_wrapper_jobs_create_sync_uses_default_base_url_when_missing() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
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
                modalities=_text_modalities(),
            )

    assert captured["url"] == f"{DEFAULT_BASE_URL.rstrip('/')}/v1/embed/jobs"
    assert captured["body"]["bucket_uid"] == BUCKET_UID


def test_wrapper_list_models_sync_uses_default_base_url() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json={"models": []}, request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            client.embedding.list_models()

    assert captured["url"] == f"{DEFAULT_BASE_URL.rstrip('/')}/v1/embed/models"
