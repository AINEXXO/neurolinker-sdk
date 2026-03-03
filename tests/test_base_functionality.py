import httpx
import pytest

from neurolinker_sdk import AsyncNeuroLinker


@pytest.mark.asyncio
async def test_base_functionality() -> None:
    """Test that the NeuroLinker client can be instantiated and make a simple API call."""
    async with AsyncNeuroLinker(token="nl_CGd6bozHhmU4asxkd-VlESSG8vep1Anm") as client:
        tasks = await client.tasks.list()
        assert isinstance(tasks, dict)
        assert "success" in tasks
