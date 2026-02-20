from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import httpx

from ..http import (
    _build_url,
    _coerce_files,
    _encode_form_payload,
    _json_headers,
    _raise_for_status,
)
from ..errors import NeuroLinkerConfigError


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
    ) -> Dict[str, Any]:
        """
        POST /api/v1/extract

        Contract (per documentation):
          - If uploading files via 'documents', then 'form' must be an empty JSON object: {}.
          - If providing URLs in 'form', then 'documents' must be an empty list: [].

        This method enforces the contract by:
          - Rejecting mixed usage (documents + urls)
          - For documents mode: forcing form="{}"
          - For urls mode: using form with documents_url + optional alias
        """
        has_docs = bool(documents)
        has_urls = bool(urls)

        if has_docs and has_urls:
            raise NeuroLinkerConfigError("Invalid extract call: provide either 'documents' or 'urls', not both.")

        url = _build_url(self._base_url, "/api/v1/extract")
        headers = _json_headers(self._token)

        if has_docs:
            # Documents mode: form must be {} and URL list must be empty.
            files = _coerce_files(documents)
            data = {"form": "{}"}
            resp = self._client.post(url, headers=headers, data=data, files=files)
            _raise_for_status(resp)
            return resp.json()

        # URLs mode: documents must be empty.
        # If neither docs nor urls were provided, that's not a valid request.
        if not has_urls:
            raise NeuroLinkerConfigError("Invalid extract call: you must provide either 'documents' or 'urls'.")

        # Build the JSON form payload (docs say the key is 'documents_url')
        form_json = _encode_form_payload(urls=urls, alias=alias)
        data = {"form": form_json}

        resp = self._client.post(url, headers=headers, data=data, files=[])
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
    ) -> Dict[str, Any]:
        """
        Async version of ExtractResource.extract().
        Enforces the same request contract described in the sync method.
        """
        has_docs = bool(documents)
        has_urls = bool(urls)

        if has_docs and has_urls:
            raise NeuroLinkerConfigError("Invalid extract call: provide either 'documents' or 'urls', not both.")

        url = _build_url(self._base_url, "/api/v1/extract")
        headers = _json_headers(self._token)

        if has_docs:
            files = _coerce_files(documents)
            data = {"form": "{}"}
            resp = await self._client.post(url, headers=headers, data=data, files=files)
            _raise_for_status(resp)
            return resp.json()

        if not has_urls:
            raise NeuroLinkerConfigError("Invalid extract call: you must provide either 'documents' or 'urls'.")

        form_json = _encode_form_payload(urls=urls, alias=alias)
        data = {"form": form_json}

        resp = await self._client.post(url, headers=headers, data=data, files=[])
        _raise_for_status(resp)
        return resp.json()