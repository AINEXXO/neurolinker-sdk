from __future__ import annotations

import os

import pytest

from neurolinker_sdk import AsyncNeuroLinker, NeuroLinker
from neurolinker_sdk.polling import (
    wait_for_terminal_status,
    wait_for_terminal_status_async,
)
from neurolinker_sdk.vector_store import (
    CollectionSchema,
    FieldDef,
    FieldMapping,
    VectorDBConfig,
)

TOKEN = os.getenv("NEUROLINKER_API_KEY")
BUCKET_UID = os.getenv("NEUROLINKER_TEST_BUCKET_UID")
VECTOR_DB_URI = os.getenv("NEUROLINKER_TEST_VECTOR_DB_URI")
VECTOR_DB_API_KEY = os.getenv("NEUROLINKER_TEST_VECTOR_DB_API_KEY")
VECTOR_DIM = int(os.getenv("NEUROLINKER_TEST_VECTOR_DIM", "1024"))

# Strict: a "pending" must not satisfy the wait — we want to actually verify
# the load job ran on the user's vector DB.
_STRICT_TERMINAL = frozenset({"completed", "failed"})

pytestmark = pytest.mark.skipif(
    not (TOKEN and BUCKET_UID and VECTOR_DB_URI and VECTOR_DB_API_KEY),
    reason=(
        "Set NEUROLINKER_API_KEY, NEUROLINKER_TEST_BUCKET_UID, "
        "NEUROLINKER_TEST_VECTOR_DB_URI and NEUROLINKER_TEST_VECTOR_DB_API_KEY "
        "to run this E2E test."
    ),
)


def _extract_status(payload: dict) -> str | None:
    s = payload.get("status")
    return s if isinstance(s, str) else None


def _collection_name() -> str:
    """Use a fixed collection name so the test is idempotent and does not
    accumulate collections on Zilliz (free tier has a 5-collection limit).
    The backend POST /collections endpoint is idempotent — re-creating an
    existing collection returns success with ``already_existed=true``.
    """
    return "sdk_e2e_stable"


def _build_collection(name: str) -> CollectionSchema:
    return CollectionSchema(
        name=name,
        description="SDK E2E test collection",
        fields=[
            FieldDef(name="chunk_id", dtype="text", is_primary=True),
            FieldDef(name="content", dtype="text"),
            FieldDef(name="text_dense", dtype="dense_vector", dim=VECTOR_DIM),
        ],
    )


def _vdb_config() -> VectorDBConfig:
    return VectorDBConfig(uri=VECTOR_DB_URI, api_key=VECTOR_DB_API_KEY)


def _field_mappings() -> list[FieldMapping]:
    return [
        FieldMapping(name="chunk_id", source="item_id"),
        FieldMapping(name="content", source="item_content"),
        # ``text_dense_e2e`` matches the ``vector_name`` used in the embedding
        # E2E test — the two tests share the same bucket conventions.
        FieldMapping(name="text_dense", source="text_dense_e2e"),
    ]


def test_e2e_vector_store_full_flow_sync() -> None:
    name = _collection_name()
    with NeuroLinker.from_env() as client:
        # 1) create collection (idempotent)
        create_resp = client.vector_store.collections.create(
            collection=_build_collection(name),
            vector_db_config=_vdb_config(),
        )
        assert isinstance(create_resp, dict)
        assert create_resp.get("success") is True
        print(
            f"[vector_store e2e] collection {name} created "
            f"(already_existed={create_resp.get('already_existed')})"
        )

        # 2) submit load job
        submit = client.vector_store.jobs.create(
            bucket_uid=BUCKET_UID,
            collection_name=name,
            field_mappings=_field_mappings(),
            vector_db_config=_vdb_config(),
        )
        job_uid = submit.get("job_uid")
        assert isinstance(job_uid, str) and job_uid, (
            f"Missing job_uid in submit response: {submit}"
        )
        print(f"[vector_store e2e] submitted load job {job_uid}")

        # 3) strict wait
        final = wait_for_terminal_status(
            fetch_status=lambda: client.vector_store.jobs.get(BUCKET_UID, job_uid),
            extract_status=_extract_status,
            timeout_s=1100.0,
            poll_interval_s=2.0,
            poll_max_interval_s=10.0,
            terminal_states=_STRICT_TERMINAL,
            identifier=f"vector-load job {job_uid}",
        )
        print(
            f"[vector_store e2e] final status: {final.get('status')}; "
            f"collection_name: {final.get('collection_name')}"
        )
        assert final.get("status") == "completed", f"Job not completed: {final}"
        assert final.get("collection_name") == name


@pytest.mark.asyncio
async def test_e2e_vector_store_full_flow_async() -> None:
    name = _collection_name()
    async with AsyncNeuroLinker.from_env() as client:
        create_resp = await client.vector_store.collections.create(
            collection=_build_collection(name),
            vector_db_config=_vdb_config(),
        )
        assert isinstance(create_resp, dict)
        assert create_resp.get("success") is True
        print(
            f"[vector_store e2e async] collection {name} created "
            f"(already_existed={create_resp.get('already_existed')})"
        )

        submit = await client.vector_store.jobs.create(
            bucket_uid=BUCKET_UID,
            collection_name=name,
            field_mappings=_field_mappings(),
            vector_db_config=_vdb_config(),
        )
        job_uid = submit.get("job_uid")
        assert isinstance(job_uid, str) and job_uid
        print(f"[vector_store e2e async] submitted load job {job_uid}")

        async def _fetch() -> dict:
            return await client.vector_store.jobs.get(BUCKET_UID, job_uid)

        final = await wait_for_terminal_status_async(
            fetch_status=_fetch,
            extract_status=_extract_status,
            timeout_s=1100.0,
            poll_interval_s=2.0,
            poll_max_interval_s=10.0,
            terminal_states=_STRICT_TERMINAL,
            identifier=f"vector-load job {job_uid}",
        )
        print(
            f"[vector_store e2e async] final status: {final.get('status')}; "
            f"collection_name: {final.get('collection_name')}"
        )
        assert final.get("status") == "completed", f"Job not completed: {final}"
        assert final.get("collection_name") == name
