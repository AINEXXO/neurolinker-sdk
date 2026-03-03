import httpx
import pytest

from neurolinker_sdk import AsyncNeuroLinker
from neurolinker_sdk.config import DEFAULT_BASE_URL
from neurolinker_sdk.errors import NeuroLinkerAPIError


@pytest.mark.asyncio
async def test_async_client_uses_default_base_url_when_not_provided() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"success": True}, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        async with AsyncNeuroLinker(
            token="nl_dummy", http_client=http_client, timeout_s=1.0
        ) as client:
            payload = await client.tasks.list()

    assert payload["success"] is True
    assert seen["url"] == f"{DEFAULT_BASE_URL}/v1/tasks"


@pytest.mark.asyncio
async def test_wait_for_request_completion_async_handles_transient_404() -> None:
    attempts = iter(
        [
            NeuroLinkerAPIError(
                status_code=404,
                method="GET",
                url="https://neurolinker.api.ainexxo.com/v1/request-status/req-async",
                response_text="not found",
            ),
            {"status": "running"},
            {"status": "completed", "request_uid": "req-async"},
        ]
    )

    async with AsyncNeuroLinker(
        token="nl_dummy",
        timeout_s=1.0,
        poll_interval_s=0.0,
        poll_max_interval_s=0.0,
    ) as client:

        async def fake_request(_: str):
            item = next(attempts)
            if isinstance(item, Exception):
                raise item
            return item

        client.status.request = fake_request

        result = await client.wait_for_request_completion("req-async")

    assert result["status"] == "completed"


@pytest.mark.asyncio
async def test_async_static_helper_methods_are_exposed() -> None:
    assert AsyncNeuroLinker.extract_request_uid({"request_uid": "req-x"}) == "req-x"
    assert AsyncNeuroLinker.extract_document_ids({"documents": [{"id": "doc-x"}]}) == ["doc-x"]
