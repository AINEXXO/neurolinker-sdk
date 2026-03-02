import httpx
import pytest

from neurolinker_sdk import NeuroLinker
from neurolinker_sdk.config import DEFAULT_BASE_URL
from neurolinker_sdk.errors import NeuroLinkerAPIError


def test_sync_client_uses_default_base_url_when_not_provided() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"success": True}, request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            payload = client.tasks.list()

    assert payload["success"] is True
    assert seen["url"] == f"{DEFAULT_BASE_URL}/v1/tasks"


def test_extract_request_uid_accepts_top_level_or_data() -> None:
    assert NeuroLinker.extract_request_uid({"request_uid": "req-top"}) == "req-top"
    assert NeuroLinker.extract_request_uid({"data": {"request_uid": "req-data"}}) == "req-data"


def test_extract_request_uid_raises_on_missing_value() -> None:
    with pytest.raises(ValueError):
        NeuroLinker.extract_request_uid({"success": True})


def test_extract_document_ids_accepts_document_id_or_id() -> None:
    top = {"documents": [{"document_id": "doc-1"}, {"id": "doc-2"}]}
    nested = {"data": {"documents": [{"document_id": "doc-3"}, {"id": "doc-4"}]}}

    assert NeuroLinker.extract_document_ids(top) == ["doc-1", "doc-2"]
    assert NeuroLinker.extract_document_ids(nested) == ["doc-3", "doc-4"]


def test_wait_for_request_completion_sync_handles_transient_404() -> None:
    attempts = iter(
        [
            NeuroLinkerAPIError(
                status_code=404,
                method="GET",
                url="https://neurolinker.api.ainexxo.com/v1/request-status/req-1",
                response_text="not found",
            ),
            {"status": "running"},
            {"status": "completed", "request_uid": "req-1"},
        ]
    )

    with NeuroLinker(
        token="nl_dummy", timeout_s=1.0, poll_interval_s=0.0, poll_max_interval_s=0.0
    ) as client:

        def fake_request(_: str):
            item = next(attempts)
            if isinstance(item, Exception):
                raise item
            return item

        client.status.request = fake_request

        result = client.wait_for_request_completion("req-1")

    assert result["status"] == "completed"
