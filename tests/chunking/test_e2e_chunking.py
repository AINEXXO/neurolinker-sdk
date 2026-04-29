import os

import pytest

from neurolinker_sdk import AsyncNeuroLinker, NeuroLinker
from neurolinker_sdk.chunking import SectionGreedyConfig

TOKEN = os.getenv("NEUROLINKER_API_KEY")
BUCKET_UID = os.getenv("NEUROLINKER_TEST_BUCKET_UID")

pytestmark = pytest.mark.skipif(
    not TOKEN or not BUCKET_UID,
    reason="Set NEUROLINKER_API_KEY and NEUROLINKER_TEST_BUCKET_UID to run this E2E test.",
)


def _assert_terminal_status(payload: dict) -> None:
    """The backend returns one of pending/processing/completed/failed."""
    assert isinstance(payload, dict)
    assert payload.get("status") in {"completed", "failed", "pending"}, (
        f"Unexpected status in chunking job payload: {payload}"
    )


def test_e2e_chunking_full_flow_sync() -> None:
    """
    Sync end-to-end chunking flow:
      1) submit job with a Pydantic config
      2) wait for completion
      3) analyze the bucket
      4) download produced files
    """
    with NeuroLinker.from_env() as client:
        # 1) submit
        submit = client.chunking.jobs.create(
            bucket_uid=BUCKET_UID,
            chunking=SectionGreedyConfig(t_min=100, t_max=512),
        )
        job_uid = submit.get("job_uid")
        assert isinstance(job_uid, str) and job_uid, f"Missing job_uid in submit response: {submit}"

        # 2) wait
        final = client.chunking.jobs.wait(job_uid)
        _assert_terminal_status(final)

        # 3) analyze
        analyze = client.chunking.analyze(BUCKET_UID)
        assert isinstance(analyze, dict)
        assert analyze.get("success") is True

        # 4) results
        files = client.chunking.results(BUCKET_UID)
        assert isinstance(files, dict)
        # When the job completed at least one file should be available.
        if final.get("status") == "completed":
            assert files, f"Expected non-empty files dict on completed job, got: {files}"
            for name, content in files.items():
                assert isinstance(name, str) and name
                assert isinstance(content, (bytes, bytearray)) and len(content) > 0


@pytest.mark.asyncio
async def test_e2e_chunking_full_flow_async() -> None:
    """Async equivalent of the full chunking flow."""
    async with AsyncNeuroLinker.from_env() as client:
        submit = await client.chunking.jobs.create(
            bucket_uid=BUCKET_UID,
            chunking=SectionGreedyConfig(t_min=100, t_max=512),
        )
        job_uid = submit.get("job_uid")
        assert isinstance(job_uid, str) and job_uid

        final = await client.chunking.jobs.wait(job_uid)
        _assert_terminal_status(final)

        analyze = await client.chunking.analyze(BUCKET_UID)
        assert isinstance(analyze, dict)
        assert analyze.get("success") is True

        files = await client.chunking.results(BUCKET_UID)
        assert isinstance(files, dict)
        if final.get("status") == "completed":
            assert files
            for name, content in files.items():
                assert isinstance(name, str) and name
                assert isinstance(content, (bytes, bytearray)) and len(content) > 0
