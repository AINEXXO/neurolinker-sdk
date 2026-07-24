from __future__ import annotations

import json
from typing import Any, Dict

import httpx

from ...errors import NeuroLinkerAPIError, NeuroLinkerConfigError
from ...http import _build_url, _json_headers, _raise_for_status

_RESULT_FILE = "result.json"


def _extract_result_url(body: Dict[str, Any]) -> str:
    """Pull the signed ``result.json`` URL out of a /results response, or raise a
    clear error when the result isn't available yet (job still running)."""
    result = body.get("result") or {}
    url = (result.get("files") or {}).get(_RESULT_FILE)
    if not url:
        detail = result.get("error") or body.get("message") or "result not yet available"
        raise NeuroLinkerConfigError(
            f"Results not available for this evaluation ({detail}). "
            "Wait for the job to reach 'completed' (jobs.wait) before fetching results."
        )
    return url


def _raise_for_signed_url(resp: httpx.Response) -> None:
    if 200 <= resp.status_code < 300:
        return
    raise NeuroLinkerAPIError(
        status_code=resp.status_code,
        method="GET",
        url=str(resp.request.url),
        response_text=(
            f"Failed to download result.json from its signed URL (status {resp.status_code}). "
            "The URL may have expired — call results() again to mint a fresh one."
        ),
        response_json=None,
    )


class ResultsResource:
    """Fetch the per-row scores + summary of a completed one-shot evaluation."""

    def __init__(self, base_url: str, token: str, client: httpx.Client):
        self._base_url = base_url
        self._token = token
        self._client = client

    def results(self, eval_uid: str) -> Dict[str, Any]:
        """POST /v1/eval/oneshot/results then download the signed ``result.json``.
        Returns the parsed JSON: ``{eval_uid, rows: [...], summary: {...}}``."""
        if not eval_uid:
            raise NeuroLinkerConfigError("eval_uid must be a non-empty string.")
        resp = self._client.post(
            _build_url(self._base_url, "/v1/eval/oneshot/results"),
            json={"eval_uid": eval_uid},
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        url = _extract_result_url(resp.json())
        file_resp = self._client.get(url)
        _raise_for_signed_url(file_resp)
        return json.loads(file_resp.content)


class AsyncResultsResource:
    """Async twin of :class:`ResultsResource`."""

    def __init__(self, base_url: str, token: str, client: httpx.AsyncClient):
        self._base_url = base_url
        self._token = token
        self._client = client

    async def results(self, eval_uid: str) -> Dict[str, Any]:
        if not eval_uid:
            raise NeuroLinkerConfigError("eval_uid must be a non-empty string.")
        resp = await self._client.post(
            _build_url(self._base_url, "/v1/eval/oneshot/results"),
            json={"eval_uid": eval_uid},
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        url = _extract_result_url(resp.json())
        file_resp = await self._client.get(url)
        _raise_for_signed_url(file_resp)
        return json.loads(file_resp.content)
