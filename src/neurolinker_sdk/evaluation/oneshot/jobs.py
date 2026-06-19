from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import httpx

from ...errors import NeuroLinkerConfigError
from ...http import _build_url, _json_headers, _raise_for_status
from ...polling import wait_for_terminal_status, wait_for_terminal_status_async

_TERMINAL_STATES = frozenset({"completed", "failed"})


def _coerce_dataset(dataset: Tuple[str, bytes]) -> List[Tuple[str, Tuple[str, bytes, str]]]:
    """Build the httpx multipart payload for the JSONL upload.

    The backend reads a single ``file`` form field and accepts only ``.jsonl``.
    The dataset is passed in memory as ``(filename, bytes)`` — the SDK never
    touches the filesystem (same convention as extraction)."""
    if not isinstance(dataset, tuple) or len(dataset) != 2:
        raise NeuroLinkerConfigError("dataset must be a (filename, bytes) tuple.")
    filename, content = dataset
    if not filename or not filename.lower().endswith(".jsonl"):
        raise NeuroLinkerConfigError("dataset filename must end with '.jsonl'.")
    if not content:
        raise NeuroLinkerConfigError("dataset content must be non-empty bytes.")
    return [("file", (filename, content, "application/x-ndjson"))]


class JobsResource:
    """One-shot evaluation jobs: upload a JSONL dataset, poll, fetch results."""

    def __init__(
        self,
        base_url: str,
        token: str,
        client: httpx.Client,
        *,
        timeout_s: float,
        poll_interval_s: float,
        poll_max_interval_s: float,
    ):
        self._base_url = base_url
        self._token = token
        self._client = client
        self._timeout_s = timeout_s
        self._poll_interval_s = poll_interval_s
        self._poll_max_interval_s = poll_max_interval_s

    def create(self, *, dataset: Tuple[str, bytes]) -> Dict[str, Any]:
        """POST /v1/eval/oneshot/jobs — upload the JSONL dataset and enqueue the
        job in one shot. Returns the body carrying ``eval_uid`` + ``status``."""
        files = _coerce_dataset(dataset)
        resp = self._client.post(
            _build_url(self._base_url, "/v1/eval/oneshot/jobs"),
            headers=_json_headers(self._token),
            files=files,
        )
        _raise_for_status(resp)
        return resp.json()

    def get(self, eval_uid: str) -> Dict[str, Any]:
        """GET /v1/eval/oneshot/jobs/{eval_uid} — current status + (on completion)
        the metric summary and result path."""
        if not eval_uid:
            raise NeuroLinkerConfigError("eval_uid must be a non-empty string.")
        resp = self._client.get(
            _build_url(self._base_url, f"/v1/eval/oneshot/jobs/{eval_uid}"),
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        return resp.json()

    def wait(
        self,
        eval_uid: str,
        *,
        timeout_s: Optional[float] = None,
        poll_interval_s: Optional[float] = None,
        poll_max_interval_s: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Poll ``get`` until the job reaches a terminal state (completed/failed)."""
        return wait_for_terminal_status(
            fetch_status=lambda: self.get(eval_uid),
            extract_status=lambda r: r.get("status"),
            timeout_s=self._timeout_s if timeout_s is None else timeout_s,
            poll_interval_s=self._poll_interval_s if poll_interval_s is None else poll_interval_s,
            poll_max_interval_s=(
                self._poll_max_interval_s if poll_max_interval_s is None else poll_max_interval_s
            ),
            terminal_states=_TERMINAL_STATES,
            identifier=f"evaluation job {eval_uid}",
        )


class AsyncJobsResource:
    """Async twin of :class:`JobsResource`."""

    def __init__(
        self,
        base_url: str,
        token: str,
        client: httpx.AsyncClient,
        *,
        timeout_s: float,
        poll_interval_s: float,
        poll_max_interval_s: float,
    ):
        self._base_url = base_url
        self._token = token
        self._client = client
        self._timeout_s = timeout_s
        self._poll_interval_s = poll_interval_s
        self._poll_max_interval_s = poll_max_interval_s

    async def create(self, *, dataset: Tuple[str, bytes]) -> Dict[str, Any]:
        files = _coerce_dataset(dataset)
        resp = await self._client.post(
            _build_url(self._base_url, "/v1/eval/oneshot/jobs"),
            headers=_json_headers(self._token),
            files=files,
        )
        _raise_for_status(resp)
        return resp.json()

    async def get(self, eval_uid: str) -> Dict[str, Any]:
        if not eval_uid:
            raise NeuroLinkerConfigError("eval_uid must be a non-empty string.")
        resp = await self._client.get(
            _build_url(self._base_url, f"/v1/eval/oneshot/jobs/{eval_uid}"),
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        return resp.json()

    async def wait(
        self,
        eval_uid: str,
        *,
        timeout_s: Optional[float] = None,
        poll_interval_s: Optional[float] = None,
        poll_max_interval_s: Optional[float] = None,
    ) -> Dict[str, Any]:
        async def _fetch() -> Dict[str, Any]:
            return await self.get(eval_uid)

        return await wait_for_terminal_status_async(
            fetch_status=_fetch,
            extract_status=lambda r: r.get("status"),
            timeout_s=self._timeout_s if timeout_s is None else timeout_s,
            poll_interval_s=self._poll_interval_s if poll_interval_s is None else poll_interval_s,
            poll_max_interval_s=(
                self._poll_max_interval_s if poll_max_interval_s is None else poll_max_interval_s
            ),
            terminal_states=_TERMINAL_STATES,
            identifier=f"evaluation job {eval_uid}",
        )
