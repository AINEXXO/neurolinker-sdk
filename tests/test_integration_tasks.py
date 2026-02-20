import os
import pytest

TOKEN = os.getenv("NEUROLINKER_TOKEN")

pytestmark = pytest.mark.skipif(
    not TOKEN,
    reason="Set NEUROLINKER_TOKEN (or use .env + python-dotenv).",
)

def test_tasks_get_integration():
    from neurolinker_sdk._generated.configuration import Configuration
    from neurolinker_sdk._generated.api_client import ApiClient
    from neurolinker_sdk._generated.api.default_api import DefaultApi

    cfg = Configuration()

    # Bearer token: l'API accetta "Authorization: Bearer <token>"
    cfg.access_token = TOKEN

    with ApiClient(cfg) as client:
        api = DefaultApi(client)
        res = api.list_processing_tasks_api_v1_tasks_get()

    # Non sappiamo la forma esatta (pydantic model vs dict), quindi controlli “robusti”
    assert res is not None