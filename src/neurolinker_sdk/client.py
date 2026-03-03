from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Optional

import httpx

from .config import (
    DEFAULT_BASE_URL,
    DEFAULT_POLL_INTERVAL_S,
    DEFAULT_POLL_MAX_INTERVAL_S,
    DEFAULT_TIMEOUT_S,
    NeuroLinkerConfig,
)
from .errors import NeuroLinkerAPIError
from .resources.documents import AsyncDocumentsResource, DocumentsResource
from .resources.extract import AsyncExtractResource, ExtractResource
from .resources.status import AsyncStatusResource, StatusResource
from .resources.tasks import AsyncTasksResource, TasksResource
from .resources.zip import AsyncZipResource, ZipResource


def _extract_request_uid(extract_response: Dict[str, Any]) -> str:
    """Extract request UID from an extract endpoint payload."""
    if isinstance(extract_response.get("request_uid"), str):
        return extract_response["request_uid"]

    data = extract_response.get("data")
    if isinstance(data, dict) and isinstance(data.get("request_uid"), str):
        return data["request_uid"]

    raise ValueError(f"Could not find request_uid in extract response: {extract_response}")


def _extract_document_ids_from_request_status(status_response: Dict[str, Any]) -> list[str]:
    """Extract document IDs from request-status payload with minimal shape assumptions."""
    documents = status_response.get("documents")
    if documents is None and isinstance(status_response.get("data"), dict):
        documents = status_response["data"].get("documents")

    if not isinstance(documents, list):
        return []

    out: list[str] = []
    for item in documents:
        if not isinstance(item, dict):
            continue
        if isinstance(item.get("document_id"), str):
            out.append(item["document_id"])
        elif isinstance(item.get("id"), str):
            out.append(item["id"])
    return out


class NeuroLinker:
    """
    Synchronous NeuroLinker SDK client.

    Designed for WSGI servers (Flask/Django), scripts, notebooks, and any sync environment.
    """

    def __init__(
        self,
        *,
        token: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        poll_interval_s: float = DEFAULT_POLL_INTERVAL_S,
        poll_max_interval_s: float = DEFAULT_POLL_MAX_INTERVAL_S,
        http_client: Optional[httpx.Client] = None,
    ):
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._timeout_s = timeout_s
        self._poll_interval_s = poll_interval_s
        self._poll_max_interval_s = poll_max_interval_s

        self._client = http_client or httpx.Client(timeout=timeout_s)

        self.tasks = TasksResource(self._base_url, self._token, self._client)
        self.status = StatusResource(self._base_url, self._token, self._client)
        self.documents = DocumentsResource(self._base_url, self._token, self._client)
        self.extract = ExtractResource(self._base_url, self._token, self._client)
        self.zip = ZipResource(self._base_url, self._token, self._client)

    @staticmethod
    def from_env(
        timeout_s: Optional[float] = None,
        poll_interval_s: Optional[float] = None,
        poll_max_interval_s: Optional[float] = None,
    ) -> "NeuroLinker":
        cfg = NeuroLinkerConfig.from_env()
        return NeuroLinker(
            base_url=cfg.base_url,
            token=cfg.token,
            timeout_s=cfg.timeout_s if timeout_s is None else timeout_s,
            poll_interval_s=cfg.poll_interval_s if poll_interval_s is None else poll_interval_s,
            poll_max_interval_s=(
                cfg.poll_max_interval_s if poll_max_interval_s is None else poll_max_interval_s
            ),
        )

    @staticmethod
    def extract_request_uid(extract_response: Dict[str, Any]) -> str:
        return _extract_request_uid(extract_response)

    @staticmethod
    def extract_document_ids(status_response: Dict[str, Any]) -> list[str]:
        return _extract_document_ids_from_request_status(status_response)

    def wait_for_request_completion(
        self,
        request_uid: str,
        *,
        timeout_s: Optional[float] = None,
        poll_interval_s: Optional[float] = None,
        poll_max_interval_s: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Poll request-status until a terminal state or timeout."""
        wait_timeout_s = self._timeout_s if timeout_s is None else timeout_s
        interval = self._poll_interval_s if poll_interval_s is None else poll_interval_s
        max_interval = (
            self._poll_max_interval_s if poll_max_interval_s is None else poll_max_interval_s
        )
        deadline = time.time() + wait_timeout_s
        last: Optional[Dict[str, Any]] = None

        while time.time() < deadline:
            try:
                last = self.status.request(request_uid)
            except NeuroLinkerAPIError as exc:
                if exc.status_code == 404:
                    time.sleep(interval)
                    interval = min(max_interval, interval * 1.5)
                    continue
                raise

            status = last.get("status")
            if status is None and isinstance(last.get("data"), dict):
                status = last["data"].get("status")

            if status in ("completed", "failed", "pending"):
                return last

            time.sleep(interval)
            interval = min(max_interval, interval * 1.2)

        job_url = None
        if isinstance(last, dict):
            job_url = last.get("job_page_url") or (last.get("data", {}) or {}).get("job_page_url")

        raise TimeoutError(
            f"Timeout waiting for request {request_uid} after {wait_timeout_s}s. "
            f"Last status: {last}. Job URL: {job_url}"
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "NeuroLinker":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


class AsyncNeuroLinker:
    """
    Asynchronous NeuroLinker SDK client.

    Designed for ASGI servers (FastAPI), async workers, and any async environment.
    """

    def __init__(
        self,
        *,
        token: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        poll_interval_s: float = DEFAULT_POLL_INTERVAL_S,
        poll_max_interval_s: float = DEFAULT_POLL_MAX_INTERVAL_S,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._timeout_s = timeout_s
        self._poll_interval_s = poll_interval_s
        self._poll_max_interval_s = poll_max_interval_s

        self._client = http_client or httpx.AsyncClient(timeout=timeout_s)

        self.tasks = AsyncTasksResource(self._base_url, self._token, self._client)
        self.status = AsyncStatusResource(self._base_url, self._token, self._client)
        self.documents = AsyncDocumentsResource(self._base_url, self._token, self._client)
        self.extract = AsyncExtractResource(self._base_url, self._token, self._client)
        self.zip = AsyncZipResource(self._base_url, self._token, self._client)

    @staticmethod
    def from_env(
        timeout_s: Optional[float] = None,
        poll_interval_s: Optional[float] = None,
        poll_max_interval_s: Optional[float] = None,
    ) -> "AsyncNeuroLinker":
        cfg = NeuroLinkerConfig.from_env()
        return AsyncNeuroLinker(
            base_url=cfg.base_url,
            token=cfg.token,
            timeout_s=cfg.timeout_s if timeout_s is None else timeout_s,
            poll_interval_s=cfg.poll_interval_s if poll_interval_s is None else poll_interval_s,
            poll_max_interval_s=(
                cfg.poll_max_interval_s if poll_max_interval_s is None else poll_max_interval_s
            ),
        )

    @staticmethod
    def extract_request_uid(extract_response: Dict[str, Any]) -> str:
        return _extract_request_uid(extract_response)

    @staticmethod
    def extract_document_ids(status_response: Dict[str, Any]) -> list[str]:
        return _extract_document_ids_from_request_status(status_response)

    async def wait_for_request_completion(
        self,
        request_uid: str,
        *,
        timeout_s: Optional[float] = None,
        poll_interval_s: Optional[float] = None,
        poll_max_interval_s: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Async polling helper for request completion."""
        wait_timeout_s = self._timeout_s if timeout_s is None else timeout_s
        interval = self._poll_interval_s if poll_interval_s is None else poll_interval_s
        max_interval = (
            self._poll_max_interval_s if poll_max_interval_s is None else poll_max_interval_s
        )
        deadline = time.time() + wait_timeout_s
        last: Optional[Dict[str, Any]] = None

        while time.time() < deadline:
            try:
                last = await self.status.request(request_uid)
            except NeuroLinkerAPIError as exc:
                if exc.status_code == 404:
                    await asyncio.sleep(interval)
                    interval = min(max_interval, interval * 1.5)
                    continue
                raise

            status = last.get("status")
            if status is None and isinstance(last.get("data"), dict):
                status = last["data"].get("status")

            if status in ("completed", "failed", "pending"):
                return last

            await asyncio.sleep(interval)
            interval = min(max_interval, interval * 1.2)

        job_url = None
        if isinstance(last, dict):
            job_url = last.get("job_page_url") or (last.get("data", {}) or {}).get("job_page_url")

        raise TimeoutError(
            f"Timeout waiting for request {request_uid} after {wait_timeout_s}s. "
            f"Last status: {last}. Job URL: {job_url}"
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "AsyncNeuroLinker":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()
