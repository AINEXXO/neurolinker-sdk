import os
import pytest

BASE_URL = os.getenv("NEUROLINKER_BASE_URL")
TOKEN = os.getenv("NEUROLINKER_TOKEN")

pytestmark = pytest.mark.skipif(
    not BASE_URL or not TOKEN,
    reason="Set NEUROLINKER_BASE_URL and NEUROLINKER_TOKEN (or use .env + python-dotenv).",
)

def test_tasks_get_integration():
    from neurolinker_sdk._generated.configuration import Configuration
    from neurolinker_sdk._generated.api_client import ApiClient
    from neurolinker_sdk._generated.api.default_api import DefaultApi

    cfg = Configuration(host=BASE_URL)

    # Bearer token: l'API accetta "Authorization: Bearer <token>"
    cfg.access_token = TOKEN

    with ApiClient(cfg) as client:
        api = DefaultApi(client)
        res = api.list_processing_tasks_api_v1_tasks_get()

    # Non sappiamo la forma esatta (pydantic model vs dict), quindi controlli “robusti”
    assert res is not None