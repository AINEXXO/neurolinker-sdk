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
FAKE_TRACK_UID = "00000000-0000-0000-0000-000000000000"


def test_tracking_base_functionality_sync() -> None:
    """Smoke: the sync client reaches the tracking backend — reading the queries
    of a non-existent track returns a real 404, proving ingress + auth + route
    wiring (and that the API pod boots)."""
    with NeuroLinker(token=TOKEN) as client:
        with pytest.raises(NeuroLinkerAPIError) as ei:
            client.evaluation.tracking.queries(FAKE_TRACK_UID)

    assert ei.value.status_code == 404


@pytest.mark.asyncio
async def test_tracking_base_functionality_async() -> None:
    async with AsyncNeuroLinker(token=TOKEN) as client:
        with pytest.raises(NeuroLinkerAPIError) as ei:
            await client.evaluation.tracking.queries(FAKE_TRACK_UID)

    assert ei.value.status_code == 404
