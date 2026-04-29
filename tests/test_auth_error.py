import pytest
from neurolinker_sdk import NeuroLinker, NeuroLinkerAPIError


def test_auth_error_raises_on_invalid_token():
    # Auth error handling is module-agnostic; list_tasks is just a cheap vector.
    client = NeuroLinker(base_url="https://dev.ainexxo.com/neurolinker", token="nl_invalid")
    try:
        with pytest.raises(NeuroLinkerAPIError):
            client.extraction.list_tasks()
    finally:
        client.close()
