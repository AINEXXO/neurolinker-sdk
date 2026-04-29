from __future__ import annotations

import json

import httpx
import pytest

from neurolinker_sdk import AsyncNeuroLinker
from neurolinker_sdk.config import DEFAULT_BASE_URL
from neurolinker_sdk.vector_store import (
    CollectionSchema,
    FieldDef,
    FieldMapping,
    VectorDBConfig,
)

BUCKET_UID = "bkt_00000000-0000-0000-0000-000000000000"
JOB_UID = "job_00000000-0000-0000-0000-000000000000"


@pytest.mark.asyncio
async def test_wrapper_collections_create_async_uses_default_base_url() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json={"success": True}, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        async with AsyncNeuroLinker(
            token="nl_dummy", http_client=http_client, timeout_s=1.0
        ) as client:
            await client.vector_store.collections.create(
                collection=CollectionSchema(
                    name="c",
                    fields=[FieldDef(name="a", dtype="text")],
                ),
                vector_db_config=VectorDBConfig(uri="https://x"),
            )

    assert captured["url"] == f"{DEFAULT_BASE_URL.rstrip('/')}/v1/vector-store/collections"


@pytest.mark.asyncio
async def test_wrapper_jobs_get_async_uses_default_base_url() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(
            200,
            json={"job_uid": JOB_UID, "status": "completed", "bucket_uid": BUCKET_UID,
                  "collection_name": "c", "created_at": "2024-01-01T00:00:00Z"},
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        async with AsyncNeuroLinker(
            token="nl_dummy", http_client=http_client, timeout_s=1.0
        ) as client:
            await client.vector_store.jobs.get(JOB_UID)

    assert captured["url"] == f"{DEFAULT_BASE_URL.rstrip('/')}/v1/vector-store/jobs/{JOB_UID}"


@pytest.mark.asyncio
async def test_wrapper_jobs_create_async_uses_default_base_url() -> None:
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

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        async with AsyncNeuroLinker(
            token="nl_dummy", http_client=http_client, timeout_s=1.0
        ) as client:
            await client.vector_store.jobs.create(
                bucket_uid=BUCKET_UID,
                collection_name="c",
                field_mappings=[FieldMapping(name="a", source="item_id")],
                vector_db_config=VectorDBConfig(uri="https://x"),
            )

    assert captured["url"] == f"{DEFAULT_BASE_URL.rstrip('/')}/v1/vector-store/jobs"
    assert captured["body"]["bucket_uid"] == BUCKET_UID
