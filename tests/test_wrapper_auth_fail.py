import pytest
from neurolinker_sdk import NeuroLinker, NeuroLinkerAPIError


def test_wrapper_auth_fail():
    # Intentionally invalid token
    client = NeuroLinker(base_url="https://dev.ainexxo.com/neurolinker", token="nl_invalid")
    try:
        with pytest.raises(NeuroLinkerAPIError):
            client.tasks.list()
    finally:
        client.close()
