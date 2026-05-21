from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import httpx

from ..errors import NeuroLinkerConfigError
from ..http import (
    _build_url,
    _coerce_files,
    _encode_form_payload,
    _json_headers,
    _raise_for_status,
)


class EnrichmentMode(str, Enum):
    BASE = "base"
    TURBO = "turbo"


def _normalize_enrichment_mode(enrichment_mode: EnrichmentMode | str | None) -> str | None:
    if enrichment_mode is None:
        return None
    try:
        return EnrichmentMode(enrichment_mode).value
    except ValueError as exc:
        valid = tuple(mode.value for mode in EnrichmentMode)
        raise NeuroLinkerConfigError(
            f"enrichment_mode must be one of {valid}, got {enrichment_mode!r}."
        ) from exc


def _validate_submit_modes(
    *, has_docs: bool, has_urls: bool, method_label: str
) -> None:
    if has_docs and has_urls:
        raise NeuroLinkerConfigError(
            f"Invalid {method_label} call: provide either 'documents' or 'urls', not both."
        )
    if not has_docs and not has_urls:
        raise NeuroLinkerConfigError(
            f"Invalid {method_label} call: you must provide either 'documents' or 'urls'."
        )


def _validate_json_schema(json_schema: Any) -> None:
    if not isinstance(json_schema, dict):
        raise NeuroLinkerConfigError(
            "json_schema must be a dict conforming to JSON Schema Draft 7 "
            "(supported subset). Got: " + type(json_schema).__name__
        )
    if not json_schema:
        raise NeuroLinkerConfigError("json_schema cannot be empty.")


class ExtractResource:
    def __init__(self, base_url: str, token: str, client: httpx.Client):
        self._base_url = base_url
        self._token = token
        self._client = client

    def extract(
        self,
        *,
        documents: Optional[List[Tuple[str, bytes]]] = None,
        urls: Optional[List[str]] = None,
        alias: Optional[str] = None,
        description: Optional[str] = None,
        enrichment_mode: EnrichmentMode | str | None = None,
    ) -> Dict[str, Any]:
        """
        POST /v1/extract

        Contract (per documentation):
          - If uploading files via 'documents', then 'form' must be an empty JSON object: {}
            (or carry optional keys like ``enrichment_mode``).
          - If providing URLs in 'form', then 'documents' must be an empty list: [].

        ``enrichment_mode`` selects how Picture/Table content is enriched:
        ``"base"`` (default backend) for description only, ``"turbo"`` for description plus
        extracted_text and legend with surrounding-page context. Omit (``None``) to let
        the backend pick its default.

        This method enforces the contract by:
          - Rejecting mixed usage (documents + urls)
          - Building the form JSON consistently across both modes
        """
        has_docs = bool(documents)
        has_urls = bool(urls)
        _validate_submit_modes(has_docs=has_docs, has_urls=has_urls, method_label="extract")
        enrichment_mode_value = _normalize_enrichment_mode(enrichment_mode)

        url = _build_url(self._base_url, "/v1/extract")
        headers = _json_headers(self._token)

        form_json = _encode_form_payload(
            urls=urls if has_urls else None,
            alias=alias,
            description=description,
            enrichment_mode=enrichment_mode_value,
        )
        data = {"form": form_json}

        if has_docs:
            files = _coerce_files(documents)
            resp = self._client.post(url, headers=headers, data=data, files=files)
        else:
            resp = self._client.post(url, headers=headers, data=data, files=[])

        _raise_for_status(resp)
        return resp.json()

    def extract_fields(
        self,
        *,
        json_schema: Dict[str, Any],
        documents: Optional[List[Tuple[str, bytes]]] = None,
        urls: Optional[List[str]] = None,
        alias: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        POST /v1/extract-fields

        Submits PDFs plus a JSON Schema (Draft 7, supported subset) and returns
        a payload conforming to the schema for each document. Same
        documents-or-urls contract as :meth:`extract`.
        """
        has_docs = bool(documents)
        has_urls = bool(urls)
        _validate_submit_modes(has_docs=has_docs, has_urls=has_urls, method_label="extract_fields")
        _validate_json_schema(json_schema)

        url = _build_url(self._base_url, "/v1/extract-fields")
        headers = _json_headers(self._token)

        form_json = _encode_form_payload(
            urls=urls if has_urls else None,
            alias=alias,
            description=description,
            json_schema=json_schema,
        )
        data = {"form": form_json}

        if has_docs:
            files = _coerce_files(documents)
            resp = self._client.post(url, headers=headers, data=data, files=files)
        else:
            resp = self._client.post(url, headers=headers, data=data, files=[])

        _raise_for_status(resp)
        return resp.json()

    def generate_schema(self, *, description: str) -> Dict[str, Any]:
        """
        POST /v1/generate-schema

        Generates a JSON Schema from a natural-language description. Synchronous
        endpoint (no async pipeline, no credits). The returned schema already
        conforms to the supported subset expected by :meth:`extract_fields`.
        """
        if not description or not description.strip():
            raise NeuroLinkerConfigError("description must be a non-empty string.")

        url = _build_url(self._base_url, "/v1/generate-schema")
        resp = self._client.post(
            url,
            json={"description": description},
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        return resp.json()


class AsyncExtractResource:
    def __init__(self, base_url: str, token: str, client: httpx.AsyncClient):
        self._base_url = base_url
        self._token = token
        self._client = client

    async def extract(
        self,
        *,
        documents: Optional[List[Tuple[str, bytes]]] = None,
        urls: Optional[List[str]] = None,
        alias: Optional[str] = None,
        description: Optional[str] = None,
        enrichment_mode: EnrichmentMode | str | None = None,
    ) -> Dict[str, Any]:
        """
        Async version of ExtractResource.extract().
        Enforces the same request contract described in the sync method.
        ``enrichment_mode`` selects ``"base"`` (description only) or ``"turbo"``
        (description + extracted_text + legend with neighbouring-page context).
        """
        has_docs = bool(documents)
        has_urls = bool(urls)
        _validate_submit_modes(has_docs=has_docs, has_urls=has_urls, method_label="extract")
        enrichment_mode_value = _normalize_enrichment_mode(enrichment_mode)

        url = _build_url(self._base_url, "/v1/extract")
        headers = _json_headers(self._token)

        form_json = _encode_form_payload(
            urls=urls if has_urls else None,
            alias=alias,
            description=description,
            enrichment_mode=enrichment_mode_value,
        )
        data = {"form": form_json}

        if has_docs:
            files = _coerce_files(documents)
            resp = await self._client.post(url, headers=headers, data=data, files=files)
        else:
            resp = await self._client.post(url, headers=headers, data=data, files=[])

        _raise_for_status(resp)
        return resp.json()

    async def extract_fields(
        self,
        *,
        json_schema: Dict[str, Any],
        documents: Optional[List[Tuple[str, bytes]]] = None,
        urls: Optional[List[str]] = None,
        alias: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        has_docs = bool(documents)
        has_urls = bool(urls)
        _validate_submit_modes(has_docs=has_docs, has_urls=has_urls, method_label="extract_fields")
        _validate_json_schema(json_schema)

        url = _build_url(self._base_url, "/v1/extract-fields")
        headers = _json_headers(self._token)

        form_json = _encode_form_payload(
            urls=urls if has_urls else None,
            alias=alias,
            description=description,
            json_schema=json_schema,
        )
        data = {"form": form_json}

        if has_docs:
            files = _coerce_files(documents)
            resp = await self._client.post(url, headers=headers, data=data, files=files)
        else:
            resp = await self._client.post(url, headers=headers, data=data, files=[])

        _raise_for_status(resp)
        return resp.json()

    async def generate_schema(self, *, description: str) -> Dict[str, Any]:
        if not description or not description.strip():
            raise NeuroLinkerConfigError("description must be a non-empty string.")

        url = _build_url(self._base_url, "/v1/generate-schema")
        resp = await self._client.post(
            url,
            json={"description": description},
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        return resp.json()
