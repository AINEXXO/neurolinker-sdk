import os
import pytest

from neurolinker_sdk import AsyncNeuroLinker


TOKEN = os.getenv("NEUROLINKER_API_KEY")

pytestmark = pytest.mark.skipif(
    not TOKEN,
    reason="Set NEUROLINKER_API_KEY to run integration tests.",
)


@pytest.mark.asyncio
async def test_wrapper_tasks_list_async_uses_default_base_url_when_missing(monkeypatch):
    monkeypatch.delenv("NEUROLINKER_BASE_URL", raising=False)

    async with AsyncNeuroLinker.from_env() as client:
        data = await client.tasks.list()

    assert data is not None
