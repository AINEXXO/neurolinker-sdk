import os

import pytest

from neurolinker_sdk import AsyncNeuroLinker, NeuroLinker, NeuroLinkerAPIError

TOKEN = os.getenv("NEUROLINKER_API_KEY")

pytestmark = pytest.mark.skipif(
    not TOKEN,
    reason="Set NEUROLINKER_API_KEY to run integration tests.",
)


FAKE_JOB_UID = "job_00000000-0000-0000-0000-000000000000"


def test_chunking_base_functionality_sync() -> None:
    """Smoke: sync client reaches the chunking backend — a non-existent job_uid
    returns a real 404, which proves ingress + auth + route wiring are correct.
    """
    with NeuroLinker(token=TOKEN) as client:
        with pytest.raises(NeuroLinkerAPIError) as ei:
            client.chunking.jobs.get(FAKE_JOB_UID)

    assert ei.value.status_code == 404


@pytest.mark.asyncio
async def test_chunking_base_functionality_async() -> None:
    async with AsyncNeuroLinker(token=TOKEN) as client:
        with pytest.raises(NeuroLinkerAPIError) as ei:
            await client.chunking.jobs.get(FAKE_JOB_UID)

    assert ei.value.status_code == 404
