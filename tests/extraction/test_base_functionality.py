import os

import httpx
import pytest

from neurolinker_sdk import AsyncNeuroLinker

TOKEN = os.getenv("NEUROLINKER_API_KEY")
    
@pytest.mark.asyncio
async def test_base_functionality() -> None:
    """Test that the NeuroLinker client can be instantiated and make a simple API call."""
    async with AsyncNeuroLinker(token=TOKEN) as client:
        tasks = await client.extraction.list_tasks()
        assert isinstance(tasks, dict)
        assert "success" in tasks
