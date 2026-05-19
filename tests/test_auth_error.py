import pytest
from neurolinker_sdk import NeuroLinker, NeuroLinkerAPIError


def test_auth_error_raises_on_invalid_token():
    # Auth error handling is module-agnostic; list_tasks is just a cheap vector.
    # base_url is resolved by the SDK from NEUROLINKER_BASE_URL or DEFAULT_BASE_URL.
    client = NeuroLinker(token="nl_invalid")
    try:
        with pytest.raises(NeuroLinkerAPIError):
            client.extraction.list_tasks()
    finally:
        client.close()
