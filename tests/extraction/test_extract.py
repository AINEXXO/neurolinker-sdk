from __future__ import annotations

import json
import urllib.parse

import httpx
import pytest

from neurolinker_sdk import (
    AsyncNeuroLinker,
    NeuroLinker,
    NeuroLinkerConfigError,
)
from neurolinker_sdk.extraction.extract import EnrichmentMode


def _parse_form_blob(content: bytes) -> dict:
    """Extract the JSON form payload from the request body.

    httpx encodes the body as ``application/x-www-form-urlencoded`` when
    ``files`` is empty (urls-only mode), or as ``multipart/form-data`` when
    ``files`` is non-empty (documents mode). The handler captures raw bytes
    here, so we tolerate both.
    """
    decoded = content.decode("utf-8", errors="replace")
    if decoded.lstrip().startswith("form="):
        decoded_unquoted = urllib.parse.unquote_plus(decoded)
        return json.loads(decoded_unquoted[len("form="):])
    brace_start = decoded.find('{')
    assert brace_start != -1, f"No JSON payload found in body: {decoded[:200]}"
    depth = 0
    end = brace_start
    for i, ch in enumerate(decoded[brace_start:], start=brace_start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    return json.loads(decoded[brace_start:end])


def test_extract_urls_mode_omits_enrichment_mode_by_default() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["content"] = request.content
        return httpx.Response(
            200,
            json={"request_uid": "req-1", "status": "submitted"},
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            client.extraction.extract(urls=["https://example.com/a.pdf"])

    form = _parse_form_blob(captured["content"])
    assert "enrichment_mode" not in form
    assert form["documents_url"] == ["https://example.com/a.pdf"]


def test_extract_urls_mode_passes_enrichment_mode_turbo() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["content"] = request.content
        return httpx.Response(
            200,
            json={"request_uid": "req-2", "status": "submitted"},
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            client.extraction.extract(
                urls=["https://example.com/a.pdf"],
                enrichment_mode=EnrichmentMode.TURBO,
            )

    form = _parse_form_blob(captured["content"])
    assert form["enrichment_mode"] == "turbo"


def test_extract_documents_mode_passes_enrichment_mode_base() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["content"] = request.content
        return httpx.Response(
            200,
            json={"request_uid": "req-3", "status": "submitted"},
            request=request,
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        with NeuroLinker(token="nl_dummy", http_client=http_client, timeout_s=1.0) as client:
            client.extraction.extract(
                documents=[("report.pdf", b"%PDF-fake-bytes%")],
                enrichment_mode=EnrichmentMode.BASE,
            )

    body = captured["content"].decode("utf-8", errors="replace")
    assert '"enrichment_mode": "base"' in body
    assert "report.pdf" in body


@pytest.mark.asyncio
async def test_extract_async_passes_enrichment_mode_turbo() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
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
            await client.extraction.extract(
                urls=["https://example.com/a.pdf"],
                enrichment_mode="turbo",
            )

    form = _parse_form_blob(captured["content"])
    assert form["enrichment_mode"] == "turbo"


def test_extract_rejects_invalid_enrichment_mode() -> None:
    with NeuroLinker(token="nl_dummy", timeout_s=1.0) as client:
        with pytest.raises(NeuroLinkerConfigError):
            client.extraction.extract(
                urls=["https://example.com/a.pdf"],
                enrichment_mode="ultra",  # type: ignore[arg-type]
            )


@pytest.mark.asyncio
async def test_extract_async_rejects_invalid_enrichment_mode() -> None:
    async with AsyncNeuroLinker(token="nl_dummy", timeout_s=1.0) as client:
        with pytest.raises(NeuroLinkerConfigError):
            await client.extraction.extract(
                urls=["https://example.com/a.pdf"],
                enrichment_mode="fast",  # type: ignore[arg-type]
            )
