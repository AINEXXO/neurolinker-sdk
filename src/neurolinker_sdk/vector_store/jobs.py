from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

import httpx

from ..validation import normalize_pydantic, normalize_pydantic_list
from ..errors import NeuroLinkerConfigError
from ..http import _build_url, _json_headers, _raise_for_status
from ..polling import wait_for_terminal_status, wait_for_terminal_status_async
from .models import FieldMapping, VectorDBConfig


def _build_load_job_payload(
    bucket_uid: str,
    collection_name: str,
    field_mappings: List[Union[FieldMapping, Dict[str, Any]]],
    vector_db_config: Any,
    database: str,
) -> Dict[str, Any]:
    if not bucket_uid:
        raise NeuroLinkerConfigError("bucket_uid must be a non-empty string.")
    if not collection_name:
        raise NeuroLinkerConfigError("collection_name must be a non-empty string.")

    return {
        "bucket_uid": bucket_uid,
        "collection_name": collection_name,
        "field_mappings": normalize_pydantic_list(
            field_mappings, FieldMapping, label="field_mappings"
        ),
        "vector_db_config": normalize_pydantic(
            vector_db_config, VectorDBConfig, label="vector_db_config"
        ),
        "database": database or "",
    }


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
        collection_name: str,
        field_mappings: List[Union[FieldMapping, Dict[str, Any]]],
        vector_db_config: Any,
        database: str = "",
    ) -> Dict[str, Any]:
        """POST /v1/vector-store/jobs — start an async vector load job."""
        payload = _build_load_job_payload(
            bucket_uid, collection_name, field_mappings, vector_db_config, database
        )
        resp = self._client.post(
            _build_url(self._base_url, "/v1/vector-store/jobs"),
            json=payload,
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        return resp.json()

    def get(self, job_uid: str) -> Dict[str, Any]:
        """GET /v1/vector-store/jobs/{job_uid}"""
        if not job_uid:
            raise NeuroLinkerConfigError("job_uid must be a non-empty string.")

        resp = self._client.get(
            _build_url(self._base_url, f"/v1/vector-store/jobs/{job_uid}"),
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        return resp.json()

    def wait(
        self,
        job_uid: str,
        *,
        timeout_s: Optional[float] = None,
        poll_interval_s: Optional[float] = None,
        poll_max_interval_s: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Poll ``/v1/vector-store/jobs/{job_uid}`` until a terminal state or timeout."""
        return wait_for_terminal_status(
            fetch_status=lambda: self.get(job_uid),
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
            identifier=f"vector-load job {job_uid}",
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
        collection_name: str,
        field_mappings: List[Union[FieldMapping, Dict[str, Any]]],
        vector_db_config: Any,
        database: str = "",
    ) -> Dict[str, Any]:
        payload = _build_load_job_payload(
            bucket_uid, collection_name, field_mappings, vector_db_config, database
        )
        resp = await self._client.post(
            _build_url(self._base_url, "/v1/vector-store/jobs"),
            json=payload,
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        return resp.json()

    async def get(self, job_uid: str) -> Dict[str, Any]:
        if not job_uid:
            raise NeuroLinkerConfigError("job_uid must be a non-empty string.")

        resp = await self._client.get(
            _build_url(self._base_url, f"/v1/vector-store/jobs/{job_uid}"),
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        return resp.json()

    async def wait(
        self,
        job_uid: str,
        *,
        timeout_s: Optional[float] = None,
        poll_interval_s: Optional[float] = None,
        poll_max_interval_s: Optional[float] = None,
    ) -> Dict[str, Any]:
        async def _fetch() -> Dict[str, Any]:
            return await self.get(job_uid)

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
            identifier=f"vector-load job {job_uid}",
        )
