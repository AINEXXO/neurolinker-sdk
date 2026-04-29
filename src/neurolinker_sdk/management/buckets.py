from __future__ import annotations

from typing import Any, Dict, List

import httpx

from ..errors import NeuroLinkerConfigError
from ..http import _build_url, _json_headers, _raise_for_status


def _validate_sources(sources: List[Dict[str, Any]]) -> None:
    if not isinstance(sources, list) or not sources:
        raise NeuroLinkerConfigError("sources must be a non-empty list.")
    for idx, src in enumerate(sources):
        if not isinstance(src, dict):
            raise NeuroLinkerConfigError(
                f"sources[{idx}] must be a dict with 'request_uid' (and optional 'doc_uids')."
            )
        if not src.get("request_uid"):
            raise NeuroLinkerConfigError(
                f"sources[{idx}].request_uid must be a non-empty string."
            )


class BucketsResource:
    def __init__(self, base_url: str, token: str, client: httpx.Client):
        self._base_url = base_url
        self._token = token
        self._client = client

    def create(self, *, name: str) -> Dict[str, Any]:
        """POST /v1/management/buckets"""
        if not name:
            raise NeuroLinkerConfigError("name must be a non-empty string.")

        resp = self._client.post(
            _build_url(self._base_url, "/v1/management/buckets"),
            json={"name": name},
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        return resp.json()

    def add_sources(
        self,
        bucket_uid: str,
        *,
        sources: List[Dict[str, Any]],
    ) -> None:
        """POST /v1/management/buckets/{bucket_uid}/sources"""
        if not bucket_uid:
            raise NeuroLinkerConfigError("bucket_uid must be a non-empty string.")
        _validate_sources(sources)

        resp = self._client.post(
            _build_url(
                self._base_url, f"/v1/management/buckets/{bucket_uid}/sources"
            ),
            json={"sources": sources},
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        return None

    def list(self) -> Dict[str, Any]:
        """GET /v1/management/buckets"""
        resp = self._client.get(
            _build_url(self._base_url, "/v1/management/buckets"),
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        return resp.json()

    def get(self, bucket_uid: str) -> Dict[str, Any]:
        """GET /v1/management/buckets/{bucket_uid}"""
        if not bucket_uid:
            raise NeuroLinkerConfigError("bucket_uid must be a non-empty string.")

        resp = self._client.get(
            _build_url(self._base_url, f"/v1/management/buckets/{bucket_uid}"),
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        return resp.json()

    def delete(self, bucket_uid: str) -> None:
        """DELETE /v1/management/buckets/{bucket_uid}"""
        if not bucket_uid:
            raise NeuroLinkerConfigError("bucket_uid must be a non-empty string.")

        resp = self._client.delete(
            _build_url(self._base_url, f"/v1/management/buckets/{bucket_uid}"),
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        return None


class AsyncBucketsResource:
    def __init__(self, base_url: str, token: str, client: httpx.AsyncClient):
        self._base_url = base_url
        self._token = token
        self._client = client

    async def create(self, *, name: str) -> Dict[str, Any]:
        if not name:
            raise NeuroLinkerConfigError("name must be a non-empty string.")

        resp = await self._client.post(
            _build_url(self._base_url, "/v1/management/buckets"),
            json={"name": name},
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        return resp.json()

    async def add_sources(
        self,
        bucket_uid: str,
        *,
        sources: List[Dict[str, Any]],
    ) -> None:
        if not bucket_uid:
            raise NeuroLinkerConfigError("bucket_uid must be a non-empty string.")
        _validate_sources(sources)

        resp = await self._client.post(
            _build_url(
                self._base_url, f"/v1/management/buckets/{bucket_uid}/sources"
            ),
            json={"sources": sources},
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        return None

    async def list(self) -> Dict[str, Any]:
        resp = await self._client.get(
            _build_url(self._base_url, "/v1/management/buckets"),
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        return resp.json()

    async def get(self, bucket_uid: str) -> Dict[str, Any]:
        if not bucket_uid:
            raise NeuroLinkerConfigError("bucket_uid must be a non-empty string.")

        resp = await self._client.get(
            _build_url(self._base_url, f"/v1/management/buckets/{bucket_uid}"),
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        return resp.json()

    async def delete(self, bucket_uid: str) -> None:
        if not bucket_uid:
            raise NeuroLinkerConfigError("bucket_uid must be a non-empty string.")

        resp = await self._client.delete(
            _build_url(self._base_url, f"/v1/management/buckets/{bucket_uid}"),
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        return None
