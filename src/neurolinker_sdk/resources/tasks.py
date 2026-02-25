from __future__ import annotations

from typing import Any, Dict

import httpx

from ..http import _build_url, _json_headers, _raise_for_status


class TasksResource:
    def __init__(self, base_url: str, token: str, client: httpx.Client):
        self._base_url = base_url
        self._token = token
        self._client = client

    def list(self) -> Dict[str, Any]:
        """
        GET /api/v1/tasks
        Returns the processing tasks available in the system.
        """
        url = _build_url(self._base_url, "/api/v1/tasks")
        resp = self._client.get(url, headers=_json_headers(self._token))
        _raise_for_status(resp)
        return resp.json()


class AsyncTasksResource:
    def __init__(self, base_url: str, token: str, client: httpx.AsyncClient):
        self._base_url = base_url
        self._token = token
        self._client = client

    async def list(self) -> Dict[str, Any]:
        url = _build_url(self._base_url, "/api/v1/tasks")
        resp = await self._client.get(url, headers=_json_headers(self._token))
        _raise_for_status(resp)
        return resp.json()
