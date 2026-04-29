from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Tuple

import httpx

from ..errors import NeuroLinkerAPIError, NeuroLinkerConfigError
from ..http import _build_url, _json_headers, _raise_for_status


def _extract_files(response_body: Dict[str, Any]) -> Dict[str, str]:
    """Read the ``result.files`` map from a `/results` response.

    The map is filename → signed URL string. Returns an empty dict if missing
    or malformed so the caller doesn't have to defensive-check.
    """
    result = response_body.get("result") or {}
    files = result.get("files") or {}
    if not isinstance(files, dict):
        return {}
    return {name: url for name, url in files.items() if isinstance(url, str) and url}


def _raise_for_signed_url_response(resp: httpx.Response, filename: str) -> None:
    if 200 <= resp.status_code < 300:
        return
    raise NeuroLinkerAPIError(
        status_code=resp.status_code,
        method="GET",
        url=str(resp.request.url),
        response_text=(
            f"Failed to fetch signed URL for '{filename}' from object storage "
            f"(status {resp.status_code}). The URL may have expired — retry the "
            f"results() call to get fresh URLs."
        ),
        response_json=None,
    )


class ResultsResource:
    def __init__(self, base_url: str, token: str, client: httpx.Client):
        self._base_url = base_url
        self._token = token
        self._client = client

    def results(self, bucket_uid: str) -> Dict[str, bytes]:
        """Fetch embedding output files for a bucket.

        Two-step flow: ``POST /v1/embed/results`` returns short-lived signed
        URLs, then each URL is fetched via HTTP GET. Returns ``{filename: bytes}``.
        """
        if not bucket_uid:
            raise NeuroLinkerConfigError("bucket_uid must be a non-empty string.")

        resp = self._client.post(
            _build_url(self._base_url, "/v1/embed/results"),
            json={"bucket_uid": bucket_uid},
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        files = _extract_files(resp.json())

        out: Dict[str, bytes] = {}
        for filename, url in files.items():
            file_resp = self._client.get(url)
            _raise_for_signed_url_response(file_resp, filename)
            out[filename] = file_resp.content
        return out


class AsyncResultsResource:
    def __init__(self, base_url: str, token: str, client: httpx.AsyncClient):
        self._base_url = base_url
        self._token = token
        self._client = client

    async def results(self, bucket_uid: str) -> Dict[str, bytes]:
        if not bucket_uid:
            raise NeuroLinkerConfigError("bucket_uid must be a non-empty string.")

        resp = await self._client.post(
            _build_url(self._base_url, "/v1/embed/results"),
            json={"bucket_uid": bucket_uid},
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        files = _extract_files(resp.json())

        targets: List[Tuple[str, str]] = list(files.items())

        async def _fetch_one(filename: str, url: str) -> Tuple[str, bytes]:
            file_resp = await self._client.get(url)
            _raise_for_signed_url_response(file_resp, filename)
            return filename, file_resp.content

        pairs = await asyncio.gather(*[_fetch_one(fn, url) for fn, url in targets])
        return dict(pairs)
