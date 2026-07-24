from __future__ import annotations

import json

import httpx
import pytest

from neurolinker_sdk import (
    AsyncNeuroLinker,
    NeuroLinker,
    NeuroLinkerConfigError,
    extract_markdown_document_ids,
)

SAMPLE_SCHEMA = {
    "type": "object",
    "properties": {
        "invoice_number": {"type": "string"},
        "total_amount": {"type": "number"},
    },
    "required": ["invoice_number"],
}

SOURCE_DOC = "3e09a9c3-f086-42b7-be39-171ce6005493"
NEW_DOC = "8354971b-653a-4597-87a1-ab9638b5c235"


# ---------------------------------------------------------------------------
# extract_fields_from_markdown — plain JSON body (no multipart, no upload)
# ---------------------------------------------------------------------------


def test_extract_fields_from_markdown_sync_posts_json_body() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "request_uid": "req-md-1",
                "status": "PENDING",
                "document_map": [{"source_document_uid": SOURCE_DOC, "document_uid": NEW_DOC}],
                "skipped": [],
            },
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            resp = client.extraction.extract_fields_from_markdown(
                json_schema=SAMPLE_SCHEMA,
                document_ids=[SOURCE_DOC],
                alias="test-alias",
                description="test desc",
            )

    assert captured["method"] == "POST"
    assert captured["url"].endswith("/v1/extract-fields-from-markdown")
    body = captured["body"]
    assert body["document_ids"] == [SOURCE_DOC]
    assert body["json_schema"] == SAMPLE_SCHEMA
    assert body["alias"] == "test-alias"
    assert body["description"] == "test desc"
    assert resp["document_map"][0]["document_uid"] == NEW_DOC


def test_extract_fields_from_markdown_omits_optional_keys() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={"request_uid": "r", "status": "PENDING", "document_map": [], "skipped": []},
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            client.extraction.extract_fields_from_markdown(
                json_schema=SAMPLE_SCHEMA, document_ids=[SOURCE_DOC]
            )

    assert "alias" not in captured["body"]
    assert "description" not in captured["body"]


@pytest.mark.asyncio
async def test_extract_fields_from_markdown_async_posts_json_body() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "request_uid": "req-md-2",
                "status": "PENDING",
                "document_map": [{"source_document_uid": SOURCE_DOC, "document_uid": NEW_DOC}],
                "skipped": [],
            },
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        async with AsyncNeuroLinker(
            token="nl_dummy", http_client=http_client, timeout_s=1.0
        ) as client:
            resp = await client.extraction.extract_fields_from_markdown(
                json_schema=SAMPLE_SCHEMA, document_ids=[SOURCE_DOC]
            )

    assert captured["url"].endswith("/v1/extract-fields-from-markdown")
    assert captured["body"]["document_ids"] == [SOURCE_DOC]
    assert resp["document_map"][0]["document_uid"] == NEW_DOC


def test_extract_fields_from_markdown_rejects_empty_document_ids() -> None:
    with NeuroLinker(token="nl_dummy", timeout_s=1.0) as client:
        with pytest.raises(NeuroLinkerConfigError):
            client.extraction.extract_fields_from_markdown(
                json_schema=SAMPLE_SCHEMA, document_ids=[]
            )


def test_extract_fields_from_markdown_rejects_bad_schema() -> None:
    with NeuroLinker(token="nl_dummy", timeout_s=1.0) as client:
        with pytest.raises(NeuroLinkerConfigError):
            client.extraction.extract_fields_from_markdown(
                json_schema={}, document_ids=[SOURCE_DOC]
            )


# ---------------------------------------------------------------------------
# documents.scalars
# ---------------------------------------------------------------------------


def test_documents_scalars_sync() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "success": True,
                "results": [
                    {
                        "document_id": NEW_DOC,
                        "format": "scalars",
                        "content": {"invoice_number": "INV-1"},
                    }
                ],
                "total": 1,
                "successful": 1,
                "failed": 0,
            },
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            resp = client.extraction.documents.scalars([NEW_DOC])

    assert captured["url"].endswith("/v1/documents/scalars")
    assert captured["body"] == {"document_ids": [NEW_DOC]}
    assert resp["results"][0]["content"]["invoice_number"] == "INV-1"


@pytest.mark.asyncio
async def test_documents_scalars_async() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={"success": True, "results": [], "total": 0, "successful": 0, "failed": 0},
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        async with AsyncNeuroLinker(
            token="nl_dummy", http_client=http_client, timeout_s=1.0
        ) as client:
            await client.extraction.documents.scalars([NEW_DOC])

    assert captured["url"].endswith("/v1/documents/scalars")
    assert captured["body"] == {"document_ids": [NEW_DOC]}


# ---------------------------------------------------------------------------
# extract_markdown_document_ids helper
# ---------------------------------------------------------------------------


def test_extract_markdown_document_ids_pulls_new_uids() -> None:
    submit_response = {
        "request_uid": "r",
        "document_map": [
            {"source_document_uid": SOURCE_DOC, "document_uid": NEW_DOC},
            {"source_document_uid": "src2", "document_uid": "new2"},
        ],
    }
    assert extract_markdown_document_ids(submit_response) == [NEW_DOC, "new2"]


def test_extract_markdown_document_ids_handles_missing_map() -> None:
    assert extract_markdown_document_ids({"request_uid": "r"}) == []


def test_extract_markdown_document_ids_handles_data_envelope_and_bad_items() -> None:
    response = {
        "data": {
            "document_map": [
                {"source_document_uid": SOURCE_DOC, "document_uid": NEW_DOC},
                {"source_document_uid": "src2"},  # no document_uid → skipped
                "not-a-dict",  # ignored
            ]
        }
    }
    assert extract_markdown_document_ids(response) == [NEW_DOC]
