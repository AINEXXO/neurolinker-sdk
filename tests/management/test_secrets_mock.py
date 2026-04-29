from __future__ import annotations

import json

import httpx
import pytest

from neurolinker_sdk import (
    AsyncNeuroLinker,
    NeuroLinker,
    NeuroLinkerAPIError,
    NeuroLinkerConfigError,
)

SECRET_ID = "neurolinker__usr_1__voyage_key"
SECRET_VALUE = "pa-super-sensitive-value-xxxxxxxxxxxxxxxxxxxx"


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


def test_secrets_create_sync_sends_name_and_value() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            201,
            json={"secret_id": SECRET_ID},
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            resp = client.management.secrets.create(
                name="voyage_key", value=SECRET_VALUE
            )

    assert captured["method"] == "POST"
    assert captured["url"].endswith("/v1/management/secrets")
    assert captured["body"] == {"name": "voyage_key", "value": SECRET_VALUE}
    assert resp["secret_id"] == SECRET_ID


def test_secrets_create_rejects_empty_value() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("HTTP call must not happen for client-side validation")

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            with pytest.raises(NeuroLinkerConfigError):
                client.management.secrets.create(name="k", value="")
            with pytest.raises(NeuroLinkerConfigError):
                client.management.secrets.create(name="", value="v")


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


def test_secrets_list_sync() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        return httpx.Response(200, json={"secrets": [SECRET_ID]}, request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            resp = client.management.secrets.list()

    assert captured["method"] == "GET"
    assert captured["url"].endswith("/v1/management/secrets")
    assert resp["secrets"] == [SECRET_ID]


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


def test_secrets_update_sync_sends_value_only_and_returns_none_on_204() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(204, request=request)

    new_value = "pa-new-value-abcdefghijklmno"

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            ret = client.management.secrets.update(SECRET_ID, value=new_value)

    assert ret is None
    assert captured["method"] == "PUT"
    assert captured["url"].endswith(f"/v1/management/secrets/{SECRET_ID}")
    assert captured["body"] == {"value": new_value}


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


def test_secrets_delete_sync_returns_none_on_204() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        return httpx.Response(204, request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            ret = client.management.secrets.delete(SECRET_ID)

    assert ret is None
    assert captured["method"] == "DELETE"
    assert captured["url"].endswith(f"/v1/management/secrets/{SECRET_ID}")


# ---------------------------------------------------------------------------
# redaction
# ---------------------------------------------------------------------------


def test_secrets_create_redacts_value_in_api_error_text_and_json() -> None:
    """If the backend echoes the secret value in an error response, the SDK
    must mask it before surfacing the ``NeuroLinkerAPIError``.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={
                "detail": f"rejected value: {SECRET_VALUE} (format invalid)",
                "echo": SECRET_VALUE,
            },
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            with pytest.raises(NeuroLinkerAPIError) as ei:
                client.management.secrets.create(name="k", value=SECRET_VALUE)

    err = ei.value
    assert SECRET_VALUE not in err.response_text
    assert "[REDACTED]" in err.response_text
    # response_json must also have the value masked out
    dumped = json.dumps(err.response_json)
    assert SECRET_VALUE not in dumped
    assert "[REDACTED]" in dumped


def test_secrets_update_redacts_value_in_api_error() -> None:
    new_value = "pa-other-very-secret-value-12345"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            500,
            text=f"internal error while storing: {new_value}",
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            with pytest.raises(NeuroLinkerAPIError) as ei:
                client.management.secrets.update(SECRET_ID, value=new_value)

    assert new_value not in ei.value.response_text
    assert "[REDACTED]" in ei.value.response_text


@pytest.mark.asyncio
async def test_secrets_create_async_redacts_value() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={"detail": f"bad value {SECRET_VALUE}"},
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        async with AsyncNeuroLinker(
            token="nl_dummy", http_client=http_client, timeout_s=1.0
        ) as client:
            with pytest.raises(NeuroLinkerAPIError) as ei:
                await client.management.secrets.create(name="k", value=SECRET_VALUE)

    assert SECRET_VALUE not in ei.value.response_text
