import os

import pytest

from neurolinker_sdk import AsyncNeuroLinker, NeuroLinker

TOKEN = os.getenv("NEUROLINKER_API_KEY")

pytestmark = pytest.mark.skipif(
    not TOKEN,
    reason="Set NEUROLINKER_API_KEY to run integration tests.",
)


def test_management_base_functionality_sync() -> None:
    """Smoke: sync client reaches the management backend — ``buckets.list`` is a
    dependency-free endpoint that returns 200 even for an empty account.
    """
    with NeuroLinker(token=TOKEN) as client:
        resp = client.management.buckets.list()

    assert isinstance(resp, dict)
    assert "buckets" in resp
    assert isinstance(resp["buckets"], list)


@pytest.mark.asyncio
async def test_management_base_functionality_async() -> None:
    async with AsyncNeuroLinker(token=TOKEN) as client:
        resp = await client.management.buckets.list()

    assert isinstance(resp, dict)
    assert "buckets" in resp
