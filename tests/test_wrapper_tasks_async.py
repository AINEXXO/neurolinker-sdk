import os
import pytest

from neurolinker_sdk import AsyncNeuroLinker


BASE_URL = os.getenv("NEUROLINKER_BASE_URL")
TOKEN = os.getenv("NEUROLINKER_TOKEN")

pytestmark = pytest.mark.skipif(
    not BASE_URL or not TOKEN,
    reason="Set NEUROLINKER_BASE_URL and NEUROLINKER_TOKEN.",
)


@pytest.mark.asyncio
async def test_wrapper_tasks_list_async():
    async with AsyncNeuroLinker.from_env() as client:
        data = await client.tasks.list()
    assert data is not None
