from __future__ import annotations

from typing import Any, Dict, Optional, List, Tuple

import httpx

from ..http import (
    _build_url,
    _json_headers,
    _raise_for_status,
    _coerce_files,
    _encode_form_payload,
)


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

        Parameters:
          - documents: list of (filename, bytes) for PDFs uploaded directly
          - urls: list of URLs to fetch PDF documents server-side
          - alias: optional alias

        The API expects multipart with:
          - "documents" (repeated file field)
          - "form" as JSON string
        """
        url = _build_url(self._base_url, "/api/v1/extract")

        files = _coerce_files(documents)
        form_json = _encode_form_payload(urls, alias)

        data = {"form": form_json}
        headers = _json_headers(self._token)

        # Important: with multipart, httpx will set Content-Type boundary automatically.
        resp = self._client.post(url, headers=headers, data=data, files=files)
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
        url = _build_url(self._base_url, "/api/v1/extract")

        files = _coerce_files(documents)
        form_json = _encode_form_payload(urls, alias)

        data = {"form": form_json}
        headers = _json_headers(self._token)

        resp = await self._client.post(url, headers=headers, data=data, files=files)
        _raise_for_status(resp)
        return resp.json()
