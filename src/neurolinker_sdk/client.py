from __future__ import annotations

from typing import Optional, Self

import httpx

from .chunking.module import AsyncChunkingModule, ChunkingModule
from .config import (
    DEFAULT_BASE_URL,
    DEFAULT_POLL_INTERVAL_S,
    DEFAULT_POLL_MAX_INTERVAL_S,
    DEFAULT_TIMEOUT_S,
    NeuroLinkerConfig,
)
from .embedding.module import AsyncEmbeddingModule, EmbeddingModule
from .evaluation.module import AsyncEvaluationModule, EvaluationModule
from .extraction.module import AsyncExtractionModule, ExtractionModule
from .management.module import AsyncManagementModule, ManagementModule
from .vector_store.module import AsyncVectorStoreModule, VectorStoreModule


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

        self.extraction = ExtractionModule(
            base_url=self._base_url,
            token=self._token,
            client=self._client,
            timeout_s=self._timeout_s,
            poll_interval_s=self._poll_interval_s,
            poll_max_interval_s=self._poll_max_interval_s,
        )
        self.chunking = ChunkingModule(
            base_url=self._base_url,
            token=self._token,
            client=self._client,
            timeout_s=self._timeout_s,
            poll_interval_s=self._poll_interval_s,
            poll_max_interval_s=self._poll_max_interval_s,
        )
        self.embedding = EmbeddingModule(
            base_url=self._base_url,
            token=self._token,
            client=self._client,
            timeout_s=self._timeout_s,
            poll_interval_s=self._poll_interval_s,
            poll_max_interval_s=self._poll_max_interval_s,
        )
        self.evaluation = EvaluationModule(
            base_url=self._base_url,
            token=self._token,
            client=self._client,
            timeout_s=self._timeout_s,
            poll_interval_s=self._poll_interval_s,
            poll_max_interval_s=self._poll_max_interval_s,
        )
        self.management = ManagementModule(
            base_url=self._base_url,
            token=self._token,
            client=self._client,
        )
        self.vector_store = VectorStoreModule(
            base_url=self._base_url,
            token=self._token,
            client=self._client,
            timeout_s=self._timeout_s,
            poll_interval_s=self._poll_interval_s,
            poll_max_interval_s=self._poll_max_interval_s,
        )

    @staticmethod
    def from_env(
        timeout_s: Optional[float] = None,
        poll_interval_s: Optional[float] = None,
        poll_max_interval_s: Optional[float] = None,
    ) -> NeuroLinker:
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

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> Self:
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

        self.extraction = AsyncExtractionModule(
            base_url=self._base_url,
            token=self._token,
            client=self._client,
            timeout_s=self._timeout_s,
            poll_interval_s=self._poll_interval_s,
            poll_max_interval_s=self._poll_max_interval_s,
        )
        self.chunking = AsyncChunkingModule(
            base_url=self._base_url,
            token=self._token,
            client=self._client,
            timeout_s=self._timeout_s,
            poll_interval_s=self._poll_interval_s,
            poll_max_interval_s=self._poll_max_interval_s,
        )
        self.embedding = AsyncEmbeddingModule(
            base_url=self._base_url,
            token=self._token,
            client=self._client,
            timeout_s=self._timeout_s,
            poll_interval_s=self._poll_interval_s,
            poll_max_interval_s=self._poll_max_interval_s,
        )
        self.evaluation = AsyncEvaluationModule(
            base_url=self._base_url,
            token=self._token,
            client=self._client,
            timeout_s=self._timeout_s,
            poll_interval_s=self._poll_interval_s,
            poll_max_interval_s=self._poll_max_interval_s,
        )
        self.management = AsyncManagementModule(
            base_url=self._base_url,
            token=self._token,
            client=self._client,
        )
        self.vector_store = AsyncVectorStoreModule(
            base_url=self._base_url,
            token=self._token,
            client=self._client,
            timeout_s=self._timeout_s,
            poll_interval_s=self._poll_interval_s,
            poll_max_interval_s=self._poll_max_interval_s,
        )

    @staticmethod
    def from_env(
        timeout_s: Optional[float] = None,
        poll_interval_s: Optional[float] = None,
        poll_max_interval_s: Optional[float] = None,
    ) -> AsyncNeuroLinker:
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

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()
