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
    extract_document_ids,
    extract_request_uid,
)
from neurolinker_sdk.extraction.helpers import extract_status
from neurolinker_sdk.polling import wait_for_terminal_status_async

# Schema aligned with the test PDF (PMSS18 — "How to Write a One Page Report"
# template). Three fields the document actually contains:
#   - title                → top heading of the document
#   - course_name          → mentioned in the footnote
#   - section_titles[].name → the visible section headings
SAMPLE_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {
            "type": "string",
            "description": "Main title of the document, shown at the top of the page",
        },
        "course_name": {
            "type": "string",
            "description": "Name of the academic course this document belongs to",
        },
        "section_titles": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of a top-level section in the document",
                    },
                },
            },
            "description": "Top-level section headings appearing in the document body",
        },
    },
    "required": ["title"],
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
            out = client.extraction.generate_schema(
                description="Extract document title and section names from a one-page report"
            )

    assert captured["method"] == "POST"
    assert captured["url"].endswith("/v1/generate-schema")
    assert captured["body"] == {
        "description": "Extract document title and section names from a one-page report"
    }
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


def test_generate_schema_api_400_raises_api_error() -> None:
    """Backend returns non-2xx → SDK propagates as ``NeuroLinkerAPIError``."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={"detail": "schema generation failed: empty model output"},
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(
            token="nl_dummy", http_client=http_client, timeout_s=1.0
        ) as client:
            with pytest.raises(NeuroLinkerAPIError) as exc_info:
                client.extraction.generate_schema(description="anything")

    assert exc_info.value.status_code == 400


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
                urls=["https://example.com/report.pdf"],
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
    assert "https://example.com/report.pdf" in body
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
                documents=[("report.pdf", b"%PDF-fake-bytes%")],
                alias="batch-2026",
            )

    assert captured["url"].endswith("/v1/extract-fields")
    body = captured["content"].decode("utf-8", errors="replace")
    # Multipart boundary means we just scan for needles; json_schema and alias must
    # appear in the form JSON, and the PDF filename must appear in the files part.
    assert "json_schema" in body
    assert "batch-2026" in body
    assert "report.pdf" in body
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
# E2E — skipped unless real credentials + PDF URL are set.
# ---------------------------------------------------------------------------


_TOKEN = os.getenv("NEUROLINKER_API_KEY")
_PDF_URL = os.getenv("NEUROLINKER_TEST_PDF_URL")

# Strict: a "pending" must not satisfy the wait — we want to actually verify
# the structured payload returned by the field-extraction pipeline.
_STRICT_TERMINAL = frozenset({"completed", "failed"})


_SUPPORTED_TYPES = {"string", "number", "integer", "boolean", "array", "object"}


def _assert_schema_in_supported_subset(schema: dict, path: str = "$") -> None:
    """Recursively assert that ``schema`` matches the subset accepted by ``extract_fields``.

    Mirrors ``extraction/pipelines/schema_validator.py`` server-side rules without
    importing them (the SDK doesn't depend on backend internals). Any deviation
    would mean the LLM produced a schema that ``extract_fields`` would later
    reject — exactly the regression we want to catch.
    """
    assert isinstance(schema, dict), f"{path}: schema node must be a dict, got {type(schema).__name__}"

    node_type = schema.get("type")
    assert isinstance(node_type, str), (
        f"{path}: 'type' must be a single string (got {node_type!r})"
    )
    assert node_type in _SUPPORTED_TYPES, (
        f"{path}: unsupported type {node_type!r}; allowed: {sorted(_SUPPORTED_TYPES)}"
    )

    # The validator allows: type, description, enum, plus per-type extras.
    common = {"type", "description", "enum"}
    if node_type == "object":
        allowed = common | {"properties", "required"}
    elif node_type == "array":
        allowed = common | {"items"}
    else:
        allowed = common
    extras = set(schema.keys()) - allowed
    assert not extras, (
        f"{path}: unsupported keywords {sorted(extras)} for type {node_type!r}; allowed: {sorted(allowed)}"
    )

    if node_type == "object":
        properties = schema.get("properties")
        assert isinstance(properties, dict) and properties, (
            f"{path}: object schema must declare a non-empty 'properties' mapping"
        )
        required = schema.get("required")
        if required is not None:
            assert isinstance(required, list) and all(isinstance(r, str) for r in required), (
                f"{path}: 'required' must be a list of strings"
            )
            unknown = [r for r in required if r not in properties]
            assert not unknown, f"{path}: 'required' references unknown properties {unknown}"
        for key, sub in properties.items():
            _assert_schema_in_supported_subset(sub, f"{path}.properties.{key}")
    elif node_type == "array":
        items = schema.get("items")
        assert items is not None, f"{path}: array schema must declare 'items'"
        assert isinstance(items, dict), (
            f"{path}: tuple-style 'items' is not supported; declare a single sub-schema"
        )
        _assert_schema_in_supported_subset(items, f"{path}.items")


@pytest.mark.asyncio
@pytest.mark.skipif(
    not _TOKEN,
    reason="NEUROLINKER_API_KEY not set — skipping field-extraction E2E against live backend.",
)
async def test_generate_schema_e2e_async() -> None:
    """E2E: ``generate_schema`` against the real backend.

    Cheap — just an LLM call, no extraction pipeline. Verifies that the
    generated schema is **structurally usable**: it conforms to the subset
    that ``extract_fields`` accepts (the backend validates this server-side
    before returning, but we re-check client-side so a regression there
    would surface here).
    """
    async with AsyncNeuroLinker.from_env() as client:
        resp = await client.extraction.generate_schema(
            description=(
                "Extract from a one-page report template: the document title (string) "
                "and the list of top-level section headings (array of objects with a 'name' field)."
            )
        )
    assert resp.get("success") is True
    schema = resp.get("json_schema")
    assert isinstance(schema, dict), f"json_schema must be a dict, got {type(schema).__name__}"

    # Root must be 'object' with non-empty properties — strict subset check.
    assert schema.get("type") == "object", f"root schema must be type 'object', got {schema.get('type')!r}"
    properties = schema.get("properties")
    assert isinstance(properties, dict) and properties, (
        f"json_schema must have a non-empty 'properties' mapping, got: {schema}"
    )

    # Recursive subset check — every sub-schema must conform.
    _assert_schema_in_supported_subset(schema)
    print(
        f"[generate_schema e2e] schema generated with {len(properties)} root property(ies): "
        + ", ".join(sorted(properties.keys()))
    )


def _pick_fields_payload(results: list) -> dict | None:
    """Return the first non-error extracted-fields payload from a documents.fields() response.

    The backend returns one entry per document_id. For documents that went through
    full extraction (not field extraction) the entry contains an error, so we skip
    those and pick the first usable payload.

    Real backend response shape (verified against the live service):
        {"format": "fields", "content": {<schema-conformant payload>}, "schema_used": {...}}
    """
    for entry in results:
        if not isinstance(entry, dict):
            continue
        if entry.get("error") or entry.get("success") is False:
            continue
        # Primary shape: entry.content holds the schema-conformant payload.
        content = entry.get("content")
        if isinstance(content, dict):
            return content
        # Fallbacks for older / alternate shapes.
        fields = entry.get("fields")
        if isinstance(fields, dict):
            return fields
        bookkeeping = {"document_id", "id", "success", "format", "schema_used", "error"}
        candidate = {k: v for k, v in entry.items() if k not in bookkeeping}
        if candidate:
            return candidate
    return None


@pytest.mark.asyncio
@pytest.mark.skipif(
    not (_TOKEN and _PDF_URL),
    reason=(
        "Set NEUROLINKER_API_KEY and NEUROLINKER_TEST_PDF_URL to run this "
        "field-extraction E2E against a real PDF."
    ),
)
async def test_extract_fields_e2e_async() -> None:
    """End-to-end: submit ``extract_fields`` against the real PDF with ``SAMPLE_SCHEMA``,
    wait until completed, and verify the structured payload via ``documents.fields``.

    The schema mirrors what the PMSS test PDF actually contains (a template
    document with a title, a course-name footnote, and several section headings).
    """
    async with AsyncNeuroLinker.from_env() as client:
        submit = await client.extraction.extract_fields(
            json_schema=SAMPLE_SCHEMA,
            urls=[_PDF_URL],
            alias="sdk-e2e-extract-fields-py",
        )
        request_uid = extract_request_uid(submit)
        print(f"[extract_fields e2e async] submitted request {request_uid}")

        async def _fetch() -> dict:
            return await client.extraction.status.request(request_uid)

        final = await wait_for_terminal_status_async(
            fetch_status=_fetch,
            extract_status=extract_status,
            timeout_s=600.0,
            poll_interval_s=2.0,
            poll_max_interval_s=10.0,
            terminal_states=_STRICT_TERMINAL,
            identifier=f"extract_fields request {request_uid}",
        )
        print(f"[extract_fields e2e async] final status: {extract_status(final)}")
        assert extract_status(final) == "completed", f"Request not completed: {final}"

        doc_uids = extract_document_ids(final)
        assert doc_uids, f"Expected at least one document_id in status: {final}"
        print(f"[extract_fields e2e async] document ids: {doc_uids}")

        fields_resp = await client.extraction.documents.fields(doc_uids)
        assert isinstance(fields_resp, dict)
        assert fields_resp.get("success") is True, f"documents.fields failed: {fields_resp}"

        results = fields_resp.get("results")
        assert isinstance(results, list) and results, (
            f"Expected non-empty results from documents.fields: {fields_resp}"
        )

        payload = _pick_fields_payload(results)
        assert payload is not None, (
            f"No usable fields payload found in results: {results}"
        )
        print(f"[extract_fields e2e async] extracted payload keys: {sorted(payload.keys())}")

        # The schema marks `title` as required, so the LLM should at least produce
        # a non-empty string for it. We assert on this; other fields are optional.
        title = payload.get("title")
        assert isinstance(title, str) and title.strip(), (
            f"Expected non-empty 'title' in extracted payload, got: {payload}"
        )
        print(f"[extract_fields e2e async] extracted title: {title!r}")
