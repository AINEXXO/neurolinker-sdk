import os

import pytest

from neurolinker_sdk import AsyncNeuroLinker, NeuroLinker
from neurolinker_sdk.embedding import (
    Content,
    EmbeddingVector,
)
from neurolinker_sdk.polling import (
    wait_for_terminal_status,
    wait_for_terminal_status_async,
)

TOKEN = os.getenv("NEUROLINKER_API_KEY")
BUCKET_UID = os.getenv("NEUROLINKER_TEST_BUCKET_UID")

# Strict: a "pending" must not satisfy the wait — we want to actually verify
# byte-level outputs of a completed job.
_STRICT_TERMINAL = frozenset({"completed", "failed"})

pytestmark = pytest.mark.skipif(
    not TOKEN or not BUCKET_UID,
    reason="Set NEUROLINKER_API_KEY and NEUROLINKER_TEST_BUCKET_UID to run this E2E test.",
)


def _extract_status(payload: dict) -> str | None:
    s = payload.get("status")
    return s if isinstance(s, str) else None


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


def _build_embeddings(model: dict) -> list[Content]:
    return [
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


def test_e2e_embedding_full_flow_sync() -> None:
    with NeuroLinker.from_env() as client:
        # 1) list models
        models = client.embedding.list_models()
        model = _pick_text_model(models)
        print(f"[embedding e2e] picked model: {model.get('name')}")

        # 2) submit job
        submit = client.embedding.jobs.create(
            bucket_uid=BUCKET_UID,
            embeddings=_build_embeddings(model),
        )
        job_uid = submit.get("job_uid")
        assert isinstance(job_uid, str) and job_uid, (
            f"Missing job_uid in submit response: {submit}"
        )
        print(f"[embedding e2e] submitted job {job_uid}")

        # 3) strict wait
        final = wait_for_terminal_status(
            fetch_status=lambda: client.embedding.jobs.get(BUCKET_UID, job_uid),
            extract_status=_extract_status,
            timeout_s=1100.0,
            poll_interval_s=2.0,
            poll_max_interval_s=10.0,
            terminal_states=_STRICT_TERMINAL,
            identifier=f"embedding job {job_uid}",
        )
        print(f"[embedding e2e] final status: {final.get('status')}")
        assert final.get("status") == "completed", f"Job not completed: {final}"

        # 4) results — real bytes verification
        files = client.embedding.results(BUCKET_UID)
        assert isinstance(files, dict)
        assert files, f"Expected non-empty files dict on completed job, got: {files}"
        for name, content in files.items():
            assert isinstance(name, str) and name
            assert isinstance(content, (bytes, bytearray)) and len(content) > 0
        print(
            f"[embedding e2e] downloaded {len(files)} files: "
            + ", ".join(f"{n} ({len(c)}B)" for n, c in files.items())
        )


@pytest.mark.asyncio
async def test_e2e_embedding_full_flow_async() -> None:
    async with AsyncNeuroLinker.from_env() as client:
        models = await client.embedding.list_models()
        model = _pick_text_model(models)
        print(f"[embedding e2e async] picked model: {model.get('name')}")

        submit = await client.embedding.jobs.create(
            bucket_uid=BUCKET_UID,
            embeddings=_build_embeddings(model),
        )
        job_uid = submit.get("job_uid")
        assert isinstance(job_uid, str) and job_uid
        print(f"[embedding e2e async] submitted job {job_uid}")

        async def _fetch() -> dict:
            return await client.embedding.jobs.get(BUCKET_UID, job_uid)

        final = await wait_for_terminal_status_async(
            fetch_status=_fetch,
            extract_status=_extract_status,
            timeout_s=1100.0,
            poll_interval_s=2.0,
            poll_max_interval_s=10.0,
            terminal_states=_STRICT_TERMINAL,
            identifier=f"embedding job {job_uid}",
        )
        print(f"[embedding e2e async] final status: {final.get('status')}")
        assert final.get("status") == "completed", f"Job not completed: {final}"

        files = await client.embedding.results(BUCKET_UID)
        assert isinstance(files, dict)
        assert files
        for name, content in files.items():
            assert isinstance(name, str) and name
            assert isinstance(content, (bytes, bytearray)) and len(content) > 0
        print(
            f"[embedding e2e async] downloaded {len(files)} files: "
            + ", ".join(f"{n} ({len(c)}B)" for n, c in files.items())
        )
