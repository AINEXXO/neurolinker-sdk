from __future__ import annotations

import os
import uuid
from typing import Iterator

import pytest

from neurolinker_sdk import AsyncNeuroLinker, NeuroLinker
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

pytestmark = pytest.mark.skipif(
    not (TOKEN and BUCKET_UID and VECTOR_DB_URI and VECTOR_DB_API_KEY),
    reason=(
        "Set NEUROLINKER_API_KEY, NEUROLINKER_TEST_BUCKET_UID, "
        "NEUROLINKER_TEST_VECTOR_DB_URI and NEUROLINKER_TEST_VECTOR_DB_API_KEY "
        "to run this E2E test."
    ),
)


@pytest.fixture(scope="session")
def vdb_secret_id() -> Iterator[str]:
    """Create a managed secret with the test vector-DB API key, yield its id, delete at teardown.

    Mirrors how a production user onboards a vector-DB credential:
    ``secrets.create`` once, reuse the returned ``secret_id`` in every job.
    The actual API key never travels in any job payload after this point.
    """
    secret_name = f"sdk_e2e_vdb_{uuid.uuid4().hex[:8]}"
    with NeuroLinker.from_env() as client:
        resp = client.management.secrets.create(
            name=secret_name, value=VECTOR_DB_API_KEY
        )
        secret_id = resp.get("secret_id")
        assert isinstance(secret_id, str) and secret_id, (
            f"secrets.create did not return a usable secret_id: {resp}"
        )
        try:
            yield secret_id
        finally:
            try:
                client.management.secrets.delete(secret_id)
            except Exception as exc:  # noqa: BLE001 — best-effort cleanup
                print(f"\n[cleanup] Warning: delete secret {secret_id}: {exc}")


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


def _vdb_config(secret_id: str) -> VectorDBConfig:
    """Build a ``VectorDBConfig`` referencing a managed secret by id.

    The ``api_key`` field is intentionally omitted — production parity.
    """
    return VectorDBConfig(uri=VECTOR_DB_URI, secret_id=secret_id)


def _field_mappings() -> list[FieldMapping]:
    return [
        FieldMapping(name="chunk_id", source="item_id"),
        FieldMapping(name="content", source="item_content"),
        # ``text_dense_e2e`` matches the ``vector_name`` used in the embedding
        # E2E test — the two tests share the same bucket conventions.
        FieldMapping(name="text_dense", source="text_dense_e2e"),
    ]


def _assert_terminal_status(payload: dict) -> None:
    assert isinstance(payload, dict)
    assert payload.get("status") in {"completed", "failed", "pending"}, (
        f"Unexpected status in vector-load job payload: {payload}"
    )


def test_e2e_vector_store_full_flow_sync(vdb_secret_id: str) -> None:
    name = _collection_name()
    with NeuroLinker.from_env() as client:
        # 1) create collection (idempotent)
        create_resp = client.vector_store.collections.create(
            collection=_build_collection(name),
            vector_db_config=_vdb_config(vdb_secret_id),
        )
        assert isinstance(create_resp, dict)
        assert create_resp.get("success") is True

        # 2) submit load job
        submit = client.vector_store.jobs.create(
            bucket_uid=BUCKET_UID,
            collection_name=name,
            field_mappings=_field_mappings(),
            vector_db_config=_vdb_config(vdb_secret_id),
        )
        job_uid = submit.get("job_uid")
        assert isinstance(job_uid, str) and job_uid, (
            f"Missing job_uid in submit response: {submit}"
        )

        # 3) wait
        final = client.vector_store.jobs.wait(job_uid)
        _assert_terminal_status(final)
        assert final.get("collection_name") == name


@pytest.mark.asyncio
async def test_e2e_vector_store_full_flow_async(vdb_secret_id: str) -> None:
    name = _collection_name()
    async with AsyncNeuroLinker.from_env() as client:
        create_resp = await client.vector_store.collections.create(
            collection=_build_collection(name),
            vector_db_config=_vdb_config(vdb_secret_id),
        )
        assert isinstance(create_resp, dict)
        assert create_resp.get("success") is True

        submit = await client.vector_store.jobs.create(
            bucket_uid=BUCKET_UID,
            collection_name=name,
            field_mappings=_field_mappings(),
            vector_db_config=_vdb_config(vdb_secret_id),
        )
        job_uid = submit.get("job_uid")
        assert isinstance(job_uid, str) and job_uid

        final = await client.vector_store.jobs.wait(job_uid)
        _assert_terminal_status(final)
        assert final.get("collection_name") == name
