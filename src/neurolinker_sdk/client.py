from __future__ import annotations

from typing import Optional

import httpx

from .config import NeuroLinkerConfig
from .resources.tasks import TasksResource, AsyncTasksResource
from .resources.status import StatusResource, AsyncStatusResource
from .resources.documents import DocumentsResource, AsyncDocumentsResource
from .resources.extract import ExtractResource, AsyncExtractResource


class NeuroLinker:
    """
    Synchronous NeuroLinker SDK client.

    Designed for WSGI servers (Flask/Django), scripts, notebooks, and any sync environment.
    """

    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        timeout_s: float = 30.0,
        http_client: Optional[httpx.Client] = None,
    ):
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._timeout_s = timeout_s

        self._client = http_client or httpx.Client(timeout=timeout_s)

        # Facade-like resources:
        self.tasks = TasksResource(self._base_url, self._token, self._client)
        self.status = StatusResource(self._base_url, self._token, self._client)
        self.documents = DocumentsResource(self._base_url, self._token, self._client)
        self.extract = ExtractResource(self._base_url, self._token, self._client)

    @staticmethod
    def from_env(timeout_s: float = 30.0) -> "NeuroLinker":
        cfg = NeuroLinkerConfig.from_env()
        return NeuroLinker(base_url=cfg.base_url, token=cfg.token, timeout_s=timeout_s)

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
        base_url: str,
        token: str,
        timeout_s: float = 30.0,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._timeout_s = timeout_s

        self._client = http_client or httpx.AsyncClient(timeout=timeout_s)

        self.tasks = AsyncTasksResource(self._base_url, self._token, self._client)
        self.status = AsyncStatusResource(self._base_url, self._token, self._client)
        self.documents = AsyncDocumentsResource(self._base_url, self._token, self._client)
        self.extract = AsyncExtractResource(self._base_url, self._token, self._client)

    @staticmethod
    def from_env(timeout_s: float = 30.0) -> "AsyncNeuroLinker":
        cfg = NeuroLinkerConfig.from_env()
        return AsyncNeuroLinker(base_url=cfg.base_url, token=cfg.token, timeout_s=timeout_s)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "AsyncNeuroLinker":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()
