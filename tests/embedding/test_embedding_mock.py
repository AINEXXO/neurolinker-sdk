from __future__ import annotations

import json

import httpx
import pytest

from neurolinker_sdk import AsyncNeuroLinker, NeuroLinker, NeuroLinkerConfigError
from neurolinker_sdk.embedding import Content, EmbeddingVector

BUCKET_UID = "bkt_00000000-0000-0000-0000-000000000000"
JOB_UID = "job_00000000-0000-0000-0000-000000000000"


def _text_only_embeddings() -> list[Content]:
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


def test_create_job_with_content_models_sync() -> None:
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
                "message": "enqueued",
            },
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            resp = client.embedding.jobs.create(
                bucket_uid=BUCKET_UID,
                embeddings=_text_only_embeddings(),
            )

    assert captured["url"].endswith("/v1/embed/jobs")
    assert captured["body"]["bucket_uid"] == BUCKET_UID
    assert captured["body"]["embeddings"][0]["vectors"][0]["field_name"] == "text_dense_bge"
    assert resp["job_uid"] == JOB_UID


def test_create_job_with_dict_payload_sync() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(200, json={"success": True, "job_uid": JOB_UID, "status": "pending", "bucket_uid": BUCKET_UID}, request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            client.embedding.jobs.create(
                bucket_uid=BUCKET_UID,
                embeddings=[
                    {
                        "content_type": "text",
                        "inputs": ["content"],
                        "vectors": [
                            {
                                "vector_type": "dense",
                                "field_name": "text_dense_bge",
                                "model_name": "ainexxo-bge-m3",
                            },
                        ],
                    }
                ],
            )

    assert captured["body"]["embeddings"][0]["vectors"][0]["field_name"] == "text_dense_bge"


def test_create_job_with_multi_vector_sync() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(200, json={"success": True, "job_uid": JOB_UID, "status": "pending", "bucket_uid": BUCKET_UID}, request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            client.embedding.jobs.create(
                bucket_uid=BUCKET_UID,
                embeddings=[
                    Content(
                        content_type="text",
                        inputs=["content", "header_path"],
                        vectors=[
                            EmbeddingVector(
                                vector_type="dense",
                                field_name="text_dense_bge",
                                model_name="ainexxo-bge-m3",
                            ),
                            EmbeddingVector(
                                vector_type="sparse",
                                field_name="text_sparse_splade",
                                model_name="ainexxo-splade",
                            ),
                        ],
                    ),
                    Content(
                        content_type="image",
                        inputs=["image_base64", "description"],
                        vectors=[
                            EmbeddingVector(
                                vector_type="dense",
                                field_name="image_dense_jina",
                                model_name="jina_ai/jina-embeddings-v4",
                                api_key="jina-key",
                            ),
                        ],
                    ),
                ],
            )

    text_vectors = captured["body"]["embeddings"][0]["vectors"]
    image_vectors = captured["body"]["embeddings"][1]["vectors"]
    assert text_vectors[0]["field_name"] == "text_dense_bge"
    assert text_vectors[1]["field_name"] == "text_sparse_splade"
    assert image_vectors[0]["field_name"] == "image_dense_jina"


def test_create_job_rejects_invalid_embeddings() -> None:
    with NeuroLinker(token="nl_dummy", timeout_s=1.0) as client:
        with pytest.raises(NeuroLinkerConfigError):
            client.embedding.jobs.create(
                bucket_uid=BUCKET_UID,
                embeddings=[
                    {
                        "content_type": "text",
                        "inputs": ["content"],
                        "vectors": [
                            {
                                "vector_type": "dense",
                                "field_name": "item_dense",
                                "model_name": "ainexxo-bge-m3",
                            },
                        ],
                    }
                ],
            )
        with pytest.raises(NeuroLinkerConfigError):
            client.embedding.jobs.create(
                bucket_uid=BUCKET_UID,
                embeddings=[
                    {"content_type": "audio", "inputs": [], "vectors": []}
                ],
            )
        with pytest.raises(NeuroLinkerConfigError):
            client.embedding.jobs.create(bucket_uid=BUCKET_UID, embeddings=[])  # type: ignore[arg-type]
        with pytest.raises(NeuroLinkerConfigError):
            client.embedding.jobs.create(bucket_uid=BUCKET_UID, embeddings=42)  # type: ignore[arg-type]


def test_create_job_rejects_empty_bucket_uid() -> None:
    with NeuroLinker(token="nl_dummy", timeout_s=1.0) as client:
        with pytest.raises(NeuroLinkerConfigError):
            client.embedding.jobs.create(bucket_uid="", embeddings=_text_only_embeddings())


@pytest.mark.asyncio
async def test_create_job_with_multi_modal_async() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(200, json={"success": True, "job_uid": JOB_UID, "status": "pending", "bucket_uid": BUCKET_UID}, request=request)

    embeddings = [
        Content(
            content_type="text",
            inputs=["content"],
            vectors=[
                EmbeddingVector(
                    vector_type="dense",
                    field_name="text_dense_bge",
                    model_name="ainexxo-bge-m3",
                ),
                EmbeddingVector(
                    vector_type="sparse",
                    field_name="text_sparse_splade",
                    model_name="ainexxo-splade",
                ),
            ],
        ),
        Content(
            content_type="image",
            inputs=["image_base64", "description"],
            vectors=[
                EmbeddingVector(
                    vector_type="dense",
                    field_name="image_dense_jina",
                    model_name="jina_ai/jina-embeddings-v4",
                    api_key="jina-key",
                ),
            ],
        ),
    ]

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        async with AsyncNeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            await client.embedding.jobs.create(bucket_uid=BUCKET_UID, embeddings=embeddings)

    body_embeddings = captured["body"]["embeddings"]
    assert body_embeddings[0]["vectors"][0]["field_name"] == "text_dense_bge"
    assert body_embeddings[0]["vectors"][1]["field_name"] == "text_sparse_splade"
    assert body_embeddings[1]["vectors"][0]["field_name"] == "image_dense_jina"


def test_get_job_sync() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        return httpx.Response(200, json={"success": True, "job_uid": JOB_UID, "status": "completed", "bucket_uid": BUCKET_UID}, request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            resp = client.embedding.jobs.get(BUCKET_UID, JOB_UID)

    assert captured["method"] == "GET"
    assert captured["url"].endswith(f"/v1/embed/jobs/{BUCKET_UID}/{JOB_UID}")
    assert resp["status"] == "completed"
