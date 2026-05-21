from __future__ import annotations

from typing import Any, Dict

import httpx

from ..http import _build_url, _json_headers, _raise_for_status


class ModelsResource:
    def __init__(self, base_url: str, token: str, client: httpx.Client):
        self._base_url = base_url
        self._token = token
        self._client = client

    def list(self) -> Dict[str, Any]:
        """GET /v1/embed/models — list internal embedding models available on the backend."""
        resp = self._client.get(
            _build_url(self._base_url, "/v1/embed/models"),
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        return resp.json()


class AsyncModelsResource:
    def __init__(self, base_url: str, token: str, client: httpx.AsyncClient):
        self._base_url = base_url
        self._token = token
        self._client = client

    async def list(self) -> Dict[str, Any]:
        resp = await self._client.get(
            _build_url(self._base_url, "/v1/embed/models"),
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        return resp.json()
