from __future__ import annotations

from typing import Any, Dict, Optional

import httpx
from pydantic import BaseModel, TypeAdapter

from ..validation import normalize_pydantic
from ..errors import NeuroLinkerConfigError
from ..http import _build_url, _json_headers, _raise_for_status
from ..polling import wait_for_terminal_status, wait_for_terminal_status_async
from .models import ChunkingConfig

_chunking_adapter: TypeAdapter = TypeAdapter(ChunkingConfig)

_TERMINAL_STATES = frozenset({"completed", "failed"})


class JobsResource:
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

    def create(
        self,
        *,
        bucket_uid: str,
        chunking: ChunkingConfig | Dict[str, Any],
    ) -> Dict[str, Any]:
        """POST /v1/chunk/jobs"""
        if not bucket_uid:
            raise NeuroLinkerConfigError("bucket_uid must be a non-empty string.")

        payload = {
            "bucket_uid": bucket_uid,
            "chunking": normalize_pydantic(
                chunking, _chunking_adapter, label="chunking config"
            ),
        }
        resp = self._client.post(
            _build_url(self._base_url, "/v1/chunk/jobs"),
            json=payload,
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        return resp.json()

    def get(self, bucket_uid: str, job_uid: str) -> Dict[str, Any]:
        """GET /v1/chunk/jobs/{bucket_uid}/{job_uid}"""
        if not bucket_uid:
            raise NeuroLinkerConfigError("bucket_uid must be a non-empty string.")
        if not job_uid:
            raise NeuroLinkerConfigError("job_uid must be a non-empty string.")

        resp = self._client.get(
            _build_url(self._base_url, f"/v1/chunk/jobs/{bucket_uid}/{job_uid}"),
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        return resp.json()

    def wait(
        self,
        bucket_uid: str,
        job_uid: str,
        *,
        timeout_s: Optional[float] = None,
        poll_interval_s: Optional[float] = None,
        poll_max_interval_s: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Poll ``/v1/chunk/jobs/{bucket_uid}/{job_uid}`` until a terminal state or timeout."""
        return wait_for_terminal_status(
            fetch_status=lambda: self.get(bucket_uid, job_uid),
            extract_status=lambda r: r.get("status"),
            timeout_s=self._timeout_s if timeout_s is None else timeout_s,
            poll_interval_s=(
                self._poll_interval_s if poll_interval_s is None else poll_interval_s
            ),
            poll_max_interval_s=(
                self._poll_max_interval_s
                if poll_max_interval_s is None
                else poll_max_interval_s
            ),
            terminal_states=_TERMINAL_STATES,
            identifier=f"chunking job {job_uid}",
        )


class AsyncJobsResource:
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

    async def create(
        self,
        *,
        bucket_uid: str,
        chunking: ChunkingConfig | Dict[str, Any],
    ) -> Dict[str, Any]:
        if not bucket_uid:
            raise NeuroLinkerConfigError("bucket_uid must be a non-empty string.")

        payload = {
            "bucket_uid": bucket_uid,
            "chunking": normalize_pydantic(
                chunking, _chunking_adapter, label="chunking config"
            ),
        }
        resp = await self._client.post(
            _build_url(self._base_url, "/v1/chunk/jobs"),
            json=payload,
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        return resp.json()

    async def get(self, bucket_uid: str, job_uid: str) -> Dict[str, Any]:
        """GET /v1/chunk/jobs/{bucket_uid}/{job_uid}"""
        if not bucket_uid:
            raise NeuroLinkerConfigError("bucket_uid must be a non-empty string.")
        if not job_uid:
            raise NeuroLinkerConfigError("job_uid must be a non-empty string.")

        resp = await self._client.get(
            _build_url(self._base_url, f"/v1/chunk/jobs/{bucket_uid}/{job_uid}"),
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        return resp.json()

    async def wait(
        self,
        bucket_uid: str,
        job_uid: str,
        *,
        timeout_s: Optional[float] = None,
        poll_interval_s: Optional[float] = None,
        poll_max_interval_s: Optional[float] = None,
    ) -> Dict[str, Any]:
        async def _fetch() -> Dict[str, Any]:
            return await self.get(bucket_uid, job_uid)

        return await wait_for_terminal_status_async(
            fetch_status=_fetch,
            extract_status=lambda r: r.get("status"),
            timeout_s=self._timeout_s if timeout_s is None else timeout_s,
            poll_interval_s=(
                self._poll_interval_s if poll_interval_s is None else poll_interval_s
            ),
            poll_max_interval_s=(
                self._poll_max_interval_s
                if poll_max_interval_s is None
                else poll_max_interval_s
            ),
            terminal_states=_TERMINAL_STATES,
            identifier=f"chunking job {job_uid}",
        )
