from __future__ import annotations

from typing import Any, Dict

import httpx

from ..http import _build_url, _json_headers, _raise_for_status


class StatusResource:
    def __init__(self, base_url: str, token: str, client: httpx.Client):
        self._base_url = base_url
        self._token = token
        self._client = client

    def request(self, request_id: str) -> Dict[str, Any]:
        """
        GET /v1/request-status/{request_id}
        """
        url = _build_url(self._base_url, f"/v1/request-status/{request_id}")
        resp = self._client.get(url, headers=_json_headers(self._token))
        _raise_for_status(resp)
        return resp.json()

    def document(self, document_id: str) -> Dict[str, Any]:
        """
        GET /v1/document-status/{document_id}
        """
        url = _build_url(self._base_url, f"/v1/document-status/{document_id}")
        resp = self._client.get(url, headers=_json_headers(self._token))
        _raise_for_status(resp)
        return resp.json()


class AsyncStatusResource:
    def __init__(self, base_url: str, token: str, client: httpx.AsyncClient):
        self._base_url = base_url
        self._token = token
        self._client = client

    async def request(self, request_id: str) -> Dict[str, Any]:
        url = _build_url(self._base_url, f"/v1/request-status/{request_id}")
        resp = await self._client.get(url, headers=_json_headers(self._token))
        _raise_for_status(resp)
        return resp.json()

    async def document(self, document_id: str) -> Dict[str, Any]:
        url = _build_url(self._base_url, f"/v1/document-status/{document_id}")
        resp = await self._client.get(url, headers=_json_headers(self._token))
        _raise_for_status(resp)
        return resp.json()
