from __future__ import annotations

import json

import httpx
import pytest

from neurolinker_sdk import AsyncNeuroLinker, NeuroLinker, NeuroLinkerConfigError
from neurolinker_sdk.vector_store import (
    CollectionSchema,
    FieldDef,
    FieldMapping,
    VectorDBConfig,
)

BUCKET_UID = "bkt_00000000-0000-0000-0000-000000000000"
JOB_UID = "job_00000000-0000-0000-0000-000000000000"


def _collection() -> CollectionSchema:
    return CollectionSchema(
        name="neurolinker_docs",
        description="test",
        fields=[
            FieldDef(name="chunk_id", dtype="text", is_primary=True),
            FieldDef(name="content", dtype="text",
                     options={"enable_analyzer": True}),
            FieldDef(name="text_dense", dtype="dense_vector", dim=1024),
            FieldDef(name="text_sparse", dtype="sparse_vector"),
        ],
    )


def _vdb_config() -> VectorDBConfig:
    return VectorDBConfig(uri="https://example.zilliz.com", secret_id="test-secret")


def _field_mappings() -> list[FieldMapping]:
    return [
        FieldMapping(name="chunk_id", source="item_id"),
        FieldMapping(name="content", source="item_content"),
        FieldMapping(name="text_dense", source="text_dense_bge"),
        FieldMapping(name="text_sparse", source="text_sparse_splade"),
    ]


# ---------------------------------------------------------------------------
# collections.create
# ---------------------------------------------------------------------------


def test_collections_create_sync_sends_correct_payload() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={"success": True, "message": "created", "collection": "neurolinker_docs",
                  "fields_count": 4, "already_existed": False},
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            resp = client.vector_store.collections.create(
                collection=_collection(),
                vector_db_config=_vdb_config(),
            )

    assert captured["method"] == "POST"
    assert captured["url"].endswith("/v1/vector-store/collections")
    body = captured["body"]
    assert body["collection"]["name"] == "neurolinker_docs"
    assert len(body["collection"]["fields"]) == 4
    assert body["collection"]["fields"][0]["is_primary"] is True
    assert body["collection"]["fields"][2]["dim"] == 1024
    assert body["vector_db_config"]["uri"] == "https://example.zilliz.com"
    # Default database == "" is sent to the backend
    assert body["database"] == ""
    assert resp["already_existed"] is False


def test_collections_create_with_dict_payload() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(200, json={"success": True}, request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            client.vector_store.collections.create(
                collection={
                    "name": "c",
                    "fields": [{"name": "a", "dtype": "text"}],
                },
                vector_db_config={"uri": "https://example", "secret_id": "s"},
                database="tenant_a",
            )

    assert captured["body"]["database"] == "tenant_a"


def test_collections_create_rejects_invalid_collection_dict() -> None:
    with NeuroLinker(token="nl_dummy", timeout_s=1.0) as client:
        # dense_vector without dim
        with pytest.raises(NeuroLinkerConfigError):
            client.vector_store.collections.create(
                collection={
                    "name": "c",
                    "fields": [{"name": "v", "dtype": "dense_vector"}],
                },
                vector_db_config={"uri": "https://x"},
            )


@pytest.mark.asyncio
async def test_collections_create_async() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json={"success": True, "already_existed": True},
                              request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        async with AsyncNeuroLinker(
            token="nl_dummy", http_client=http_client, timeout_s=1.0
        ) as client:
            resp = await client.vector_store.collections.create(
                collection=_collection(),
                vector_db_config=_vdb_config(),
            )

    assert captured["url"].endswith("/v1/vector-store/collections")
    assert resp["already_existed"] is True


# ---------------------------------------------------------------------------
# jobs.create
# ---------------------------------------------------------------------------


def test_jobs_create_sync_sends_correct_payload() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={"success": True, "job_uid": JOB_UID, "status": "pending",
                  "message": "queued", "bucket_uid": BUCKET_UID},
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            resp = client.vector_store.jobs.create(
                bucket_uid=BUCKET_UID,
                collection_name="neurolinker_docs",
                field_mappings=_field_mappings(),
                vector_db_config=_vdb_config(),
            )

    assert captured["url"].endswith("/v1/vector-store/jobs")
    body = captured["body"]
    assert body["bucket_uid"] == BUCKET_UID
    assert body["collection_name"] == "neurolinker_docs"
    assert len(body["field_mappings"]) == 4
    assert body["field_mappings"][0] == {"name": "chunk_id", "source": "item_id"}
    assert body["database"] == ""
    assert resp["job_uid"] == JOB_UID


def test_jobs_create_accepts_dict_field_mappings() -> None:
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
            client.vector_store.jobs.create(
                bucket_uid=BUCKET_UID,
                collection_name="c",
                field_mappings=[{"name": "a", "source": "item_id"}],
                vector_db_config={"uri": "https://x"},
            )

    assert captured["body"]["field_mappings"] == [
        {"name": "a", "source": "item_id"},
    ]


def test_jobs_create_rejects_empty_inputs() -> None:
    with NeuroLinker(token="nl_dummy", timeout_s=1.0) as client:
        with pytest.raises(NeuroLinkerConfigError):
            client.vector_store.jobs.create(
                bucket_uid="",
                collection_name="c",
                field_mappings=_field_mappings(),
                vector_db_config=_vdb_config(),
            )
        with pytest.raises(NeuroLinkerConfigError):
            client.vector_store.jobs.create(
                bucket_uid=BUCKET_UID,
                collection_name="",
                field_mappings=_field_mappings(),
                vector_db_config=_vdb_config(),
            )
        with pytest.raises(NeuroLinkerConfigError):
            client.vector_store.jobs.create(
                bucket_uid=BUCKET_UID,
                collection_name="c",
                field_mappings=[],
                vector_db_config=_vdb_config(),
            )


def test_jobs_create_rejects_invalid_field_mapping() -> None:
    with NeuroLinker(token="nl_dummy", timeout_s=1.0) as client:
        with pytest.raises(NeuroLinkerConfigError):
            client.vector_store.jobs.create(
                bucket_uid=BUCKET_UID,
                collection_name="c",
                field_mappings=[{"name": "a"}],  # missing source
                vector_db_config=_vdb_config(),
            )


# ---------------------------------------------------------------------------
# jobs.get
# ---------------------------------------------------------------------------


def test_jobs_get_sync() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        return httpx.Response(
            200,
            json={"job_uid": JOB_UID, "status": "completed", "bucket_uid": BUCKET_UID,
                  "collection_name": "c", "total_records": 42,
                  "created_at": "2024-01-01T00:00:00Z"},
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            resp = client.vector_store.jobs.get(JOB_UID)

    assert captured["method"] == "GET"
    assert captured["url"].endswith(f"/v1/vector-store/jobs/{JOB_UID}")
    assert resp["status"] == "completed"
    assert resp["total_records"] == 42


def test_jobs_get_rejects_empty_job_uid() -> None:
    with NeuroLinker(token="nl_dummy", timeout_s=1.0) as client:
        with pytest.raises(NeuroLinkerConfigError):
            client.vector_store.jobs.get("")


# ---------------------------------------------------------------------------
# jobs.wait
# ---------------------------------------------------------------------------


def test_jobs_wait_sync_polls_until_terminal() -> None:
    statuses = iter([
        {"job_uid": JOB_UID, "status": "processing"},
        {"job_uid": JOB_UID, "status": "processing"},
        {"job_uid": JOB_UID, "status": "completed"},
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
            final = client.vector_store.jobs.wait(JOB_UID)

    assert final["status"] == "completed"


def test_jobs_wait_sync_tolerates_404_transient() -> None:
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
            final = client.vector_store.jobs.wait(JOB_UID)

    assert final["status"] == "completed"
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_jobs_wait_async_polls() -> None:
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
            final = await client.vector_store.jobs.wait(JOB_UID)

    assert final["status"] == "completed"


@pytest.mark.asyncio
async def test_jobs_create_async() -> None:
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
            await client.vector_store.jobs.create(
                bucket_uid=BUCKET_UID,
                collection_name="neurolinker_docs",
                field_mappings=_field_mappings(),
                vector_db_config=_vdb_config(),
                database="tenant_a",
            )

    assert captured["body"]["database"] == "tenant_a"
    assert captured["body"]["collection_name"] == "neurolinker_docs"
