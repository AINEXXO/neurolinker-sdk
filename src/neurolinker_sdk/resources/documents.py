from __future__ import annotations

from typing import Any, Dict, List

import httpx

from ..http import _build_url, _json_headers, _raise_for_status


class DocumentsResource:
    def __init__(self, base_url: str, token: str, client: httpx.Client):
        self._base_url = base_url
        self._token = token
        self._client = client

    def _post_ids(self, path: str, document_ids: List[str]) -> Dict[str, Any]:
        url = _build_url(self._base_url, path)
        payload = {"document_ids": document_ids}
        resp = self._client.post(url, headers=_json_headers(self._token), json=payload)
        _raise_for_status(resp)
        return resp.json()

    def markdown(self, document_ids: List[str]) -> Dict[str, Any]: #TODO: ma tutti questi tipi? Servono? l'api non è solo /api/v1/documents/{document_id} che è il path del documento di tipo string?
        return self._post_ids("/api/v1/documents/markdown", document_ids)

    def json(self, document_ids: List[str]) -> Dict[str, Any]:
        return self._post_ids("/api/v1/documents/json", document_ids)

    def images(self, document_ids: List[str]) -> Dict[str, Any]:
        return self._post_ids("/api/v1/documents/images", document_ids)

    def page_summaries(self, document_ids: List[str]) -> Dict[str, Any]:
        return self._post_ids("/api/v1/documents/page-summaries", document_ids)

    def summary(self, document_ids: List[str]) -> Dict[str, Any]:
        return self._post_ids("/api/v1/documents/summary", document_ids)


class AsyncDocumentsResource:
    def __init__(self, base_url: str, token: str, client: httpx.AsyncClient):
        self._base_url = base_url
        self._token = token
        self._client = client

    async def _post_ids(self, path: str, document_ids: List[str]) -> Dict[str, Any]:
        url = _build_url(self._base_url, path)
        payload = {"document_ids": document_ids}
        resp = await self._client.post(url, headers=_json_headers(self._token), json=payload)
        _raise_for_status(resp)
        return resp.json()

    async def markdown(self, document_ids: List[str]) -> Dict[str, Any]:
        return await self._post_ids("/api/v1/documents/markdown", document_ids)

    async def json(self, document_ids: List[str]) -> Dict[str, Any]:
        return await self._post_ids("/api/v1/documents/json", document_ids)

    async def images(self, document_ids: List[str]) -> Dict[str, Any]:
        return await self._post_ids("/api/v1/documents/images", document_ids)

    async def page_summaries(self, document_ids: List[str]) -> Dict[str, Any]:
        return await self._post_ids("/api/v1/documents/page-summaries", document_ids)

    async def summary(self, document_ids: List[str]) -> Dict[str, Any]:
        return await self._post_ids("/api/v1/documents/summary", document_ids)
