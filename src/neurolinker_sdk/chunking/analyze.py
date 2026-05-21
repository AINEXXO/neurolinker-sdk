from __future__ import annotations

from typing import Any, Dict

import httpx

from ..errors import NeuroLinkerConfigError
from ..http import _build_url, _json_headers, _raise_for_status


class AnalyzeResource:
    def __init__(self, base_url: str, token: str, client: httpx.Client):
        self._base_url = base_url
        self._token = token
        self._client = client

    def analyze(self, bucket_uid: str) -> Dict[str, Any]:
        """POST /v1/chunk/analyze.

        Generates ``chunking_statistics.json`` + ``chunking_distribution.png``
        from the existing ``chunking.msgpack`` and returns a ``ResultsResponse``
        with short-lived signed URLs to both artefacts under ``result.files``.
        """
        if not bucket_uid:
            raise NeuroLinkerConfigError("bucket_uid must be a non-empty string.")

        resp = self._client.post(
            _build_url(self._base_url, "/v1/chunk/analyze"),
            json={"bucket_uid": bucket_uid},
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        return resp.json()


class AsyncAnalyzeResource:
    def __init__(self, base_url: str, token: str, client: httpx.AsyncClient):
        self._base_url = base_url
        self._token = token
        self._client = client

    async def analyze(self, bucket_uid: str) -> Dict[str, Any]:
        if not bucket_uid:
            raise NeuroLinkerConfigError("bucket_uid must be a non-empty string.")

        resp = await self._client.post(
            _build_url(self._base_url, "/v1/chunk/analyze"),
            json={"bucket_uid": bucket_uid},
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        return resp.json()
