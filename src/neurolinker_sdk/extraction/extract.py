from __future__ import annotations

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
    ) -> Dict[str, Any]:
        """
        POST /v1/extract

        Contract (per documentation):
          - If uploading files via 'documents', then 'form' must be an empty JSON object: {}.
          - If providing URLs in 'form', then 'documents' must be an empty list: [].

        This method enforces the contract by:
          - Rejecting mixed usage (documents + urls)
          - For documents mode: forcing form="{}"
          - For urls mode: using form with documents_url + optional alias/description
        """
        has_docs = bool(documents)
        has_urls = bool(urls)
        _validate_submit_modes(has_docs=has_docs, has_urls=has_urls, method_label="extract")

        url = _build_url(self._base_url, "/v1/extract")
        headers = _json_headers(self._token)

        if has_docs:
            files = _coerce_files(documents)
            data = {"form": "{}"}
            resp = self._client.post(url, headers=headers, data=data, files=files)
            _raise_for_status(resp)
            return resp.json()

        form_json = _encode_form_payload(
            urls=urls,
            alias=alias,
            description=description,
        )
        resp = self._client.post(url, headers=headers, data={"form": form_json}, files=[])
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
    ) -> Dict[str, Any]:
        """
        Async version of ExtractResource.extract().
        Enforces the same request contract described in the sync method.
        """
        has_docs = bool(documents)
        has_urls = bool(urls)
        _validate_submit_modes(has_docs=has_docs, has_urls=has_urls, method_label="extract")

        url = _build_url(self._base_url, "/v1/extract")
        headers = _json_headers(self._token)

        if has_docs:
            files = _coerce_files(documents)
            data = {"form": "{}"}
            resp = await self._client.post(url, headers=headers, data=data, files=files)
            _raise_for_status(resp)
            return resp.json()

        form_json = _encode_form_payload(
            urls=urls,
            alias=alias,
            description=description,
        )
        resp = await self._client.post(url, headers=headers, data={"form": form_json}, files=[])
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
