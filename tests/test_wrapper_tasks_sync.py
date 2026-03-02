import os
import pytest

from neurolinker_sdk import NeuroLinker


TOKEN = os.getenv("NEUROLINKER_TOKEN")

pytestmark = pytest.mark.skipif(
    not TOKEN,
    reason="Set NEUROLINKER_TOKEN to run integration tests.",
)


def test_wrapper_tasks_list_sync_uses_default_base_url_when_missing(monkeypatch):
    # Ensure base_url is not set, but token is set
    monkeypatch.delenv("NEUROLINKER_BASE_URL", raising=False)

    with NeuroLinker.from_env() as client:
        data = client.tasks.list()

    assert data is not None
