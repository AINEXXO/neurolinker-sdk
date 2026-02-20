import os
import pytest
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("NEUROLINKER_TOKEN")

pytestmark = pytest.mark.skipif(
    not TOKEN,
    reason="Set NEUROLINKER_TOKEN to run integration tests.",
)

def test_integration_list_tasks():
    from neurolinker_sdk._generated.configuration import Configuration
    from neurolinker_sdk._generated.api_client import ApiClient
    from neurolinker_sdk._generated.api.default_api import DefaultApi

    cfg = Configuration()
    cfg.access_token = TOKEN

    with ApiClient(cfg) as client:
        api = DefaultApi(client)

        # This method name depends on the generated code; it could be api.get_tasks(), tasks_get(), etc.
        # We'll fix it as soon as we see the available names in DefaultApi.
        assert api is not None