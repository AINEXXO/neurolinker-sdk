# Test for:
# packaging/paths are correct
# imports work
# client is instantiated

def test_imports():
    from neurolinker_sdk._generated.configuration import Configuration
    from neurolinker_sdk._generated.api_client import ApiClient
    from neurolinker_sdk._generated.api.default_api import DefaultApi

    cfg = Configuration(host="http://example.com")
    client = ApiClient(configuration=cfg)
    api = DefaultApi(api_client=client)

    assert cfg.host == "http://example.com"
    assert api is not None

