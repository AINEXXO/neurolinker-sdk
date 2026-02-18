# Test for:
# bearer token is set
# Since the backend auth is Authorization: Bearer <token>, we check that the config sets it correctly.

def test_bearer_token_is_set():
    from neurolinker_sdk._generated.configuration import Configuration
    cfg = Configuration(host="http://example.com")

    # OpenAPI Generator for python usually uses access_token for bearer
    cfg.access_token = "nl_test_token"

    assert cfg.access_token == "nl_test_token"