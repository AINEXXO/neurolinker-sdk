from __future__ import annotations

import os
import uuid
from typing import Any, Dict, Optional

import pytest

from neurolinker_sdk import (
    NeuroLinker,
    extract_document_ids,
    extract_request_uid,
)
from neurolinker_sdk.chunking import SectionGreedyConfig
from neurolinker_sdk.embedding import (
    Content,
    EmbeddingVector,
)
from neurolinker_sdk.vector_store import (
    CollectionSchema,
    FieldDef,
    FieldMapping,
    VectorDBConfig,
)

TOKEN = os.getenv("NEUROLINKER_API_KEY")
PDF_URL = os.getenv("NEUROLINKER_TEST_PDF_URL")
VECTOR_DB_URI = os.getenv("NEUROLINKER_TEST_VECTOR_DB_URI")
VECTOR_DB_API_KEY = os.getenv("NEUROLINKER_TEST_VECTOR_DB_API_KEY")
VECTOR_DIM = int(os.getenv("NEUROLINKER_TEST_VECTOR_DIM", "1024"))

# Fixed collection name — re-runs are idempotent on the vector DB side
# (POST /collections returns ``already_existed=true``). Avoids accumulating
# test collections on managed clusters with low limits (e.g. Zilliz free tier).
COLLECTION_NAME = "sdk_full_e2e_stable"

pytestmark = pytest.mark.skipif(
    not (TOKEN and PDF_URL and VECTOR_DB_URI and VECTOR_DB_API_KEY),
    reason=(
        "Set NEUROLINKER_API_KEY, NEUROLINKER_TEST_PDF_URL, "
        "NEUROLINKER_TEST_VECTOR_DB_URI and NEUROLINKER_TEST_VECTOR_DB_API_KEY "
        "to run this E2E test."
    ),
)


def _pick_text_dense_model(client: NeuroLinker) -> Dict[str, Any]:
    """Return the first internal model that supports text-dense embeddings."""
    payload = client.embedding.list_models()
    models = payload.get("models")
    assert isinstance(models, list) and models, (
        f"No internal embedding models returned: {payload}"
    )
    for m in models:
        if "dense" in (m.get("vector_types") or []):
            return m
    raise AssertionError(f"No model with 'dense' vector_types in: {models}")


def test_e2e_full_pipeline_sync() -> None:
    """Extraction -> bucket -> chunk -> embed -> vector_store, all in one go."""
    suffix = uuid.uuid4().hex[:8]
    bucket_name = f"sdk-full-e2e-{suffix}"

    bucket_uid: Optional[str] = None

    with NeuroLinker.from_env() as client:
        try:
            # ----------------------------------------------------------------
            # 1) Extract a PDF
            # ----------------------------------------------------------------
            submit = client.extraction.extract(urls=[PDF_URL], alias="sdk-full-e2e")
            request_uid = extract_request_uid(submit)
            assert isinstance(request_uid, str) and request_uid

            extract_final = client.extraction.wait_for_request(request_uid)
            assert extract_final.get("status") == "completed", (
                f"Extraction did not complete: {extract_final}"
            )
            doc_uids = extract_document_ids(extract_final)
            assert doc_uids, f"No document_ids returned: {extract_final}"

            # ----------------------------------------------------------------
            # 2) Bucket — create then link the extraction request
            # ----------------------------------------------------------------
            created = client.management.buckets.create(name=bucket_name)
            bucket_uid = created.get("bucket_uid")
            assert isinstance(bucket_uid, str) and bucket_uid

            client.management.buckets.add_sources(
                bucket_uid,
                sources=[{"request_uid": request_uid, "doc_uids": doc_uids}],
            )

            # ----------------------------------------------------------------
            # 3) Chunking
            # ----------------------------------------------------------------
            chunk_submit = client.chunking.jobs.create(
                bucket_uid=bucket_uid,
                chunking=SectionGreedyConfig(t_min=100, t_max=512),
            )
            chunk_job_uid = chunk_submit.get("job_uid")
            assert isinstance(chunk_job_uid, str) and chunk_job_uid

            chunk_final = client.chunking.jobs.wait(bucket_uid, chunk_job_uid)
            assert chunk_final.get("status") == "completed", (
                f"Chunking did not complete: {chunk_final}"
            )

            # ----------------------------------------------------------------
            # 4) Embedding — internal text-dense model (no BYOK key)
            # ----------------------------------------------------------------
            model = _pick_text_dense_model(client)
            embeddings = [
                Content(
                    content_type="text",
                    inputs=["content"],
                    vectors=[
                        EmbeddingVector(
                            vector_type="dense",
                            field_name="text_dense_e2e",
                            model_name=model["name"],
                        ),
                    ],
                )
            ]
            embed_submit = client.embedding.jobs.create(
                bucket_uid=bucket_uid,
                embeddings=embeddings,
            )
            embed_job_uid = embed_submit.get("job_uid")
            assert isinstance(embed_job_uid, str) and embed_job_uid

            embed_final = client.embedding.jobs.wait(bucket_uid, embed_job_uid)
            assert embed_final.get("status") == "completed", (
                f"Embedding did not complete: {embed_final}"
            )

            # ----------------------------------------------------------------
            # 5) Vector store — create collection (idempotent) + load job
            # ----------------------------------------------------------------
            collection = CollectionSchema(
                name=COLLECTION_NAME,
                description="Cross-module SDK E2E test collection",
                fields=[
                    FieldDef(name="chunk_id", dtype="text", is_primary=True),
                    FieldDef(name="content", dtype="text"),
                    FieldDef(name="text_dense", dtype="dense_vector", dim=VECTOR_DIM),
                ],
            )
            vdb = VectorDBConfig(uri=VECTOR_DB_URI, api_key=VECTOR_DB_API_KEY)

            create_resp = client.vector_store.collections.create(
                collection=collection, vector_db_config=vdb
            )
            assert create_resp.get("success") is True, create_resp

            load_submit = client.vector_store.jobs.create(
                bucket_uid=bucket_uid,
                collection_name=COLLECTION_NAME,
                field_mappings=[
                    FieldMapping(name="chunk_id", source="item_id"),
                    FieldMapping(name="content", source="item_content"),
                    FieldMapping(name="text_dense", source="text_dense_e2e"),
                ],
                vector_db_config=vdb,
            )
            load_job_uid = load_submit.get("job_uid")
            assert isinstance(load_job_uid, str) and load_job_uid

            load_final = client.vector_store.jobs.wait(bucket_uid, load_job_uid)
            assert load_final.get("status") == "completed", (
                f"Vector-store load did not complete: {load_final}"
            )
            assert load_final.get("collection_name") == COLLECTION_NAME
        finally:
            if bucket_uid:
                try:
                    client.management.buckets.delete(bucket_uid)
                except Exception as exc:  # noqa: BLE001
                    print(f"\n[cleanup] delete bucket {bucket_uid}: {exc}")
