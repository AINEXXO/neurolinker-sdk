import os

import pytest

from neurolinker_sdk import AsyncNeuroLinker, NeuroLinker
from neurolinker_sdk.embedding import (
    EmbeddingModalities,
    ModalityVectors,
    ModelRef,
    TextModality,
    VectorConfig,
)

TOKEN = os.getenv("NEUROLINKER_API_KEY")
BUCKET_UID = os.getenv("NEUROLINKER_TEST_BUCKET_UID")

pytestmark = pytest.mark.skipif(
    not TOKEN or not BUCKET_UID,
    reason="Set NEUROLINKER_API_KEY and NEUROLINKER_TEST_BUCKET_UID to run this E2E test.",
)


def _pick_text_model(models_payload: dict) -> dict:
    """Return the first model that supports ``dense`` text embeddings."""
    models = models_payload.get("models")
    assert isinstance(models, list) and models, (
        f"No internal embedding models returned: {models_payload}"
    )
    for m in models:
        if "dense" in (m.get("vector_types") or []):
            return m
    raise AssertionError(f"No model with 'dense' vector_types in: {models}")


def _build_modalities(model: dict) -> EmbeddingModalities:
    return EmbeddingModalities(
        text=TextModality(
            vectors=ModalityVectors(
                dense=VectorConfig(
                    vector_name="text_dense_e2e",
                    model=ModelRef(
                        endpoint=model["endpoint"],
                        model_name=model["name"],
                    ),
                    inputs=["content"],
                ),
            ),
        ),
    )


def _assert_terminal_status(payload: dict) -> None:
    assert isinstance(payload, dict)
    assert payload.get("status") in {"completed", "failed", "pending"}, (
        f"Unexpected status in embedding job payload: {payload}"
    )


def test_e2e_embedding_full_flow_sync() -> None:
    with NeuroLinker.from_env() as client:
        # 1) list models
        models = client.embedding.list_models()
        model = _pick_text_model(models)

        # 2) submit job
        submit = client.embedding.jobs.create(
            bucket_uid=BUCKET_UID,
            modalities=_build_modalities(model),
        )
        job_uid = submit.get("job_uid")
        assert isinstance(job_uid, str) and job_uid, (
            f"Missing job_uid in submit response: {submit}"
        )

        # 3) wait
        final = client.embedding.jobs.wait(job_uid)
        _assert_terminal_status(final)

        # 4) results
        files = client.embedding.results(BUCKET_UID)
        assert isinstance(files, dict)
        if final.get("status") == "completed":
            assert files, f"Expected non-empty files dict on completed job, got: {files}"
            for name, content in files.items():
                assert isinstance(name, str) and name
                assert isinstance(content, (bytes, bytearray)) and len(content) > 0


@pytest.mark.asyncio
async def test_e2e_embedding_full_flow_async() -> None:
    async with AsyncNeuroLinker.from_env() as client:
        models = await client.embedding.list_models()
        model = _pick_text_model(models)

        submit = await client.embedding.jobs.create(
            bucket_uid=BUCKET_UID,
            modalities=_build_modalities(model),
        )
        job_uid = submit.get("job_uid")
        assert isinstance(job_uid, str) and job_uid

        final = await client.embedding.jobs.wait(job_uid)
        _assert_terminal_status(final)

        files = await client.embedding.results(BUCKET_UID)
        assert isinstance(files, dict)
        if final.get("status") == "completed":
            assert files
            for name, content in files.items():
                assert isinstance(name, str) and name
                assert isinstance(content, (bytes, bytearray)) and len(content) > 0
