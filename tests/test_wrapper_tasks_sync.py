import os
import pytest

from neurolinker_sdk import NeuroLinker


BASE_URL = os.getenv("NEUROLINKER_BASE_URL")
TOKEN = os.getenv("NEUROLINKER_TOKEN")

pytestmark = pytest.mark.skipif(
    not BASE_URL or not TOKEN,
    reason="Set NEUROLINKER_BASE_URL and NEUROLINKER_TOKEN.",
)


def test_wrapper_tasks_list_sync():
    with NeuroLinker.from_env() as client:
        data = client.tasks.list()
    assert data is not None
