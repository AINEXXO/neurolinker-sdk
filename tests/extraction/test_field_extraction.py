from __future__ import annotations

import json
import os
import urllib.parse

import httpx
import pytest

from neurolinker_sdk import (
    AsyncNeuroLinker,
    NeuroLinker,
    NeuroLinkerAPIError,
    NeuroLinkerConfigError,
)

SAMPLE_SCHEMA = {
    "type": "object",
    "properties": {
        "invoice_number": {"type": "string"},
        "total_amount": {"type": "number"},
    },
    "required": ["invoice_number", "total_amount"],
}


# ---------------------------------------------------------------------------
# generate_schema
# ---------------------------------------------------------------------------


def test_generate_schema_sync_posts_description_json() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={"success": True, "json_schema": SAMPLE_SCHEMA},
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(
            token="nl_dummy", http_client=http_client, timeout_s=1.0
        ) as client:
            out = client.extraction.generate_schema(description="invoice with total")

    assert captured["method"] == "POST"
    assert captured["url"].endswith("/v1/generate-schema")
    assert captured["body"] == {"description": "invoice with total"}
    assert out["json_schema"] == SAMPLE_SCHEMA


@pytest.mark.asyncio
async def test_generate_schema_async_posts_description_json() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200, json={"success": True, "json_schema": SAMPLE_SCHEMA}, request=request
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        async with AsyncNeuroLinker(
            token="nl_dummy", http_client=http_client, timeout_s=1.0
        ) as client:
            await client.extraction.generate_schema(description="async description")

    assert captured["body"] == {"description": "async description"}


def test_generate_schema_rejects_empty_description() -> None:
    with NeuroLinker(token="nl_dummy", timeout_s=1.0) as client:
        with pytest.raises(NeuroLinkerConfigError):
            client.extraction.generate_schema(description="")
        with pytest.raises(NeuroLinkerConfigError):
            client.extraction.generate_schema(description="   ")


# ---------------------------------------------------------------------------
# extract_fields
# ---------------------------------------------------------------------------


def test_extract_fields_urls_mode_includes_schema_in_form() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        captured["content"] = request.content
        return httpx.Response(
            200,
            json={"request_uid": "req-fields-1", "status": "submitted"},
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(
            token="nl_dummy", http_client=http_client, timeout_s=1.0
        ) as client:
            resp = client.extraction.extract_fields(
                json_schema=SAMPLE_SCHEMA,
                urls=["https://example.com/invoice.pdf"],
                alias="test-alias",
                description="test desc",
            )

    assert captured["method"] == "POST"
    assert captured["url"].endswith("/v1/extract-fields")
    # The form payload (multipart) must contain a JSON blob with json_schema + documents_url.
    # Body is URL-encoded multipart; decode before substring asserts.
    body = urllib.parse.unquote_plus(
        captured["content"].decode("utf-8", errors="replace")
    )
    assert "json_schema" in body
    assert "documents_url" in body
    assert "https://example.com/invoice.pdf" in body
    assert "test-alias" in body
    assert resp["request_uid"] == "req-fields-1"


def test_extract_fields_documents_mode_includes_schema_in_form() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["content"] = request.content
        return httpx.Response(
            200,
            json={"request_uid": "req-docs", "status": "submitted"},
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(
            token="nl_dummy", http_client=http_client, timeout_s=1.0
        ) as client:
            resp = client.extraction.extract_fields(
                json_schema=SAMPLE_SCHEMA,
                documents=[("inv.pdf", b"%PDF-fake-bytes%")],
                alias="batch-2026",
            )

    assert captured["url"].endswith("/v1/extract-fields")
    body = captured["content"].decode("utf-8", errors="replace")
    # Multipart boundary means we just scan for needles; json_schema and alias must
    # appear in the form JSON, and the PDF filename must appear in the files part.
    assert "json_schema" in body
    assert "batch-2026" in body
    assert "inv.pdf" in body
    # In documents mode, documents_url should NOT appear.
    assert "documents_url" not in body
    assert resp["request_uid"] == "req-docs"


@pytest.mark.asyncio
async def test_extract_fields_async_urls_mode() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["content"] = request.content
        return httpx.Response(
            200,
            json={"request_uid": "req-async", "status": "submitted"},
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        async with AsyncNeuroLinker(
            token="nl_dummy", http_client=http_client, timeout_s=1.0
        ) as client:
            resp = await client.extraction.extract_fields(
                json_schema=SAMPLE_SCHEMA,
                urls=["https://example.com/a.pdf"],
            )

    assert captured["url"].endswith("/v1/extract-fields")
    body = captured["content"].decode("utf-8", errors="replace")
    assert "json_schema" in body
    assert resp["request_uid"] == "req-async"


def test_extract_fields_rejects_mixed_documents_and_urls() -> None:
    with NeuroLinker(token="nl_dummy", timeout_s=1.0) as client:
        with pytest.raises(NeuroLinkerConfigError):
            client.extraction.extract_fields(
                json_schema=SAMPLE_SCHEMA,
                documents=[("a.pdf", b"x")],
                urls=["https://example.com/a.pdf"],
            )


def test_extract_fields_rejects_missing_documents_and_urls() -> None:
    with NeuroLinker(token="nl_dummy", timeout_s=1.0) as client:
        with pytest.raises(NeuroLinkerConfigError):
            client.extraction.extract_fields(json_schema=SAMPLE_SCHEMA)


def test_extract_fields_rejects_non_dict_schema() -> None:
    with NeuroLinker(token="nl_dummy", timeout_s=1.0) as client:
        with pytest.raises(NeuroLinkerConfigError):
            client.extraction.extract_fields(
                json_schema="not a dict",  # type: ignore[arg-type]
                urls=["https://example.com/a.pdf"],
            )


def test_extract_fields_rejects_empty_schema() -> None:
    with NeuroLinker(token="nl_dummy", timeout_s=1.0) as client:
        with pytest.raises(NeuroLinkerConfigError):
            client.extraction.extract_fields(
                json_schema={},
                urls=["https://example.com/a.pdf"],
            )


# ---------------------------------------------------------------------------
# documents.fields
# ---------------------------------------------------------------------------


def test_documents_fields_posts_document_ids() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={"success": True, "results": [], "total": 0, "successful": 0, "failed": 0},
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(
            token="nl_dummy", http_client=http_client, timeout_s=1.0
        ) as client:
            client.extraction.documents.fields(["doc-1", "doc-2"])

    assert captured["method"] == "POST"
    assert captured["url"].endswith("/v1/documents/fields")
    assert captured["body"] == {"document_ids": ["doc-1", "doc-2"]}


@pytest.mark.asyncio
async def test_documents_fields_async() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(200, json={"success": True, "results": []}, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        async with AsyncNeuroLinker(
            token="nl_dummy", http_client=http_client, timeout_s=1.0
        ) as client:
            await client.extraction.documents.fields(["doc-async-1"])

    assert captured["body"] == {"document_ids": ["doc-async-1"]}


# ---------------------------------------------------------------------------
# Backend API error propagation
# ---------------------------------------------------------------------------


def test_extract_fields_api_400_raises_api_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={"detail": "json_schema contains unsupported keyword: anyOf at /properties/x"},
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(
            token="nl_dummy", http_client=http_client, timeout_s=1.0
        ) as client:
            with pytest.raises(NeuroLinkerAPIError) as exc_info:
                client.extraction.extract_fields(
                    json_schema=SAMPLE_SCHEMA,
                    urls=["https://example.com/a.pdf"],
                )

    assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# Optional E2E — skipped unless a real API key is set.
# ---------------------------------------------------------------------------


_TOKEN = os.getenv("NEUROLINKER_API_KEY")


@pytest.mark.asyncio
@pytest.mark.skipif(
    not _TOKEN,
    reason="NEUROLINKER_API_KEY not set — skipping field-extraction E2E against live backend.",
)
async def test_generate_schema_e2e_async() -> None:
    """Smoke E2E: ``generate_schema`` against the real backend. Cheap — just LLM call."""
    async with AsyncNeuroLinker.from_env() as client:
        resp = await client.extraction.generate_schema(
            description=(
                "Extract from an invoice: invoice number (string), total amount (number)."
            )
        )
    assert resp.get("success") is True
    assert isinstance(resp.get("json_schema"), dict)
