import os

import pytest

from neurolinker_sdk import AsyncNeuroLinker, NeuroLinker, NeuroLinkerAPIError

TOKEN = os.getenv("NEUROLINKER_API_KEY")

pytestmark = pytest.mark.skipif(
    not TOKEN,
    reason="Set NEUROLINKER_API_KEY to run integration tests.",
)

# A well-formed UUID that does not belong to the caller → the backend returns a
# real 404 (never differentiating existence cross-tenant).
FAKE_EVAL_UID = "00000000-0000-0000-0000-000000000000"


def test_evaluation_base_functionality_sync() -> None:
    """Smoke: the sync client reaches the evaluation backend — a non-existent
    eval_uid returns a real 404, which proves ingress + auth + route wiring are
    correct (and that the API pod boots, e.g. no missing-dependency crash)."""
    with NeuroLinker(token=TOKEN) as client:
        with pytest.raises(NeuroLinkerAPIError) as ei:
            client.evaluation.oneshot.jobs.get(FAKE_EVAL_UID)

    assert ei.value.status_code == 404


@pytest.mark.asyncio
async def test_evaluation_base_functionality_async() -> None:
    async with AsyncNeuroLinker(token=TOKEN) as client:
        with pytest.raises(NeuroLinkerAPIError) as ei:
            await client.evaluation.oneshot.jobs.get(FAKE_EVAL_UID)

    assert ei.value.status_code == 404
