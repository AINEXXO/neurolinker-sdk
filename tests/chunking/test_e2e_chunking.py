import os

import pytest

from neurolinker_sdk import AsyncNeuroLinker, NeuroLinker
from neurolinker_sdk.chunking import SectionGreedyConfig
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


def test_e2e_chunking_full_flow_sync() -> None:
    """
    Sync end-to-end chunking flow:
      1) submit job with a Pydantic config
      2) wait until completed (strict — pending fails the test)
      3) analyze the bucket
      4) download produced files (real bytes)
    """
    with NeuroLinker.from_env() as client:
        # 1) submit
        submit = client.chunking.jobs.create(
            bucket_uid=BUCKET_UID,
            chunking=SectionGreedyConfig(t_min=100, t_max=512),
        )
        job_uid = submit.get("job_uid")
        assert isinstance(job_uid, str) and job_uid, f"Missing job_uid in submit response: {submit}"
        print(f"[chunking e2e] submitted job {job_uid}")

        # 2) strict wait
        final = wait_for_terminal_status(
            fetch_status=lambda: client.chunking.jobs.get(job_uid),
            extract_status=_extract_status,
            timeout_s=540.0,
            poll_interval_s=2.0,
            poll_max_interval_s=10.0,
            terminal_states=_STRICT_TERMINAL,
            identifier=f"chunking job {job_uid}",
        )
        print(f"[chunking e2e] final status: {final.get('status')}")
        assert final.get("status") == "completed", f"Job not completed: {final}"

        # 3) analyze
        analyze = client.chunking.analyze(BUCKET_UID)
        assert isinstance(analyze, dict)
        assert analyze.get("success") is True

        # 4) results — real bytes verification, no longer gated behind a soft if
        files = client.chunking.results(BUCKET_UID)
        assert isinstance(files, dict)
        assert files, f"Expected non-empty files dict on completed job, got: {files}"
        for name, content in files.items():
            assert isinstance(name, str) and name
            assert isinstance(content, (bytes, bytearray)) and len(content) > 0
        print(
            f"[chunking e2e] downloaded {len(files)} files: "
            + ", ".join(f"{n} ({len(c)}B)" for n, c in files.items())
        )


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
        print(f"[chunking e2e async] submitted job {job_uid}")

        async def _fetch() -> dict:
            return await client.chunking.jobs.get(job_uid)

        final = await wait_for_terminal_status_async(
            fetch_status=_fetch,
            extract_status=_extract_status,
            timeout_s=540.0,
            poll_interval_s=2.0,
            poll_max_interval_s=10.0,
            terminal_states=_STRICT_TERMINAL,
            identifier=f"chunking job {job_uid}",
        )
        print(f"[chunking e2e async] final status: {final.get('status')}")
        assert final.get("status") == "completed", f"Job not completed: {final}"

        analyze = await client.chunking.analyze(BUCKET_UID)
        assert isinstance(analyze, dict)
        assert analyze.get("success") is True

        files = await client.chunking.results(BUCKET_UID)
        assert isinstance(files, dict)
        assert files
        for name, content in files.items():
            assert isinstance(name, str) and name
            assert isinstance(content, (bytes, bytearray)) and len(content) > 0
        print(
            f"[chunking e2e async] downloaded {len(files)} files: "
            + ", ".join(f"{n} ({len(c)}B)" for n, c in files.items())
        )
