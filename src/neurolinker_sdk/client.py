from __future__ import annotations

from typing import Any, Dict, List, Optional, Self, Tuple

import httpx

from .config import (
    DEFAULT_BASE_URL,
    DEFAULT_POLL_INTERVAL_S,
    DEFAULT_POLL_MAX_INTERVAL_S,
    DEFAULT_TIMEOUT_S,
    NeuroLinkerConfig,
)
from .polling import wait_for_terminal_status, wait_for_terminal_status_async
from .chunking.analyze import AnalyzeResource, AsyncAnalyzeResource
from .chunking.results import AsyncResultsResource, ResultsResource
from .chunking.jobs import (
    AsyncJobsResource as AsyncChunkingJobsResource,
)
from .chunking.jobs import JobsResource as ChunkingJobsResource
from .embedding.results import (
    AsyncResultsResource as AsyncEmbeddingResultsResource,
)
from .embedding.results import ResultsResource as EmbeddingResultsResource
from .embedding.jobs import (
    AsyncJobsResource as AsyncEmbeddingJobsResource,
)
from .embedding.jobs import JobsResource as EmbeddingJobsResource
from .embedding.models_api import (
    AsyncModelsResource as AsyncEmbeddingModelsResource,
)
from .embedding.models_api import ModelsResource as EmbeddingModelsResource
from .extraction.documents import AsyncDocumentsResource, DocumentsResource
from .extraction.extract import AsyncExtractResource, EnrichmentMode, ExtractResource
from .extraction.helpers import (
    extract_document_ids as _extract_document_ids,
    extract_request_uid as _extract_request_uid,
    extract_status,
)
from .extraction.status import AsyncStatusResource, StatusResource
from .extraction.tasks import AsyncTasksResource, TasksResource
from .extraction.zip import AsyncZipResource, ZipResource
from .management.buckets import AsyncBucketsResource, BucketsResource
from .vector_store.collections import (
    AsyncCollectionsResource as AsyncVectorStoreCollectionsResource,
)
from .vector_store.collections import (
    CollectionsResource as VectorStoreCollectionsResource,
)
from .vector_store.jobs import (
    AsyncJobsResource as AsyncVectorStoreJobsResource,
)
from .vector_store.jobs import JobsResource as VectorStoreJobsResource


def _extraction_timeout_suffix(last: Optional[Dict[str, Any]]) -> str:
    """Return ``" Job URL: <url>"`` from a request-status payload, or ``""``."""
    if not isinstance(last, dict):
        return ""
    url = last.get("job_page_url")
    if not url:
        data = last.get("data")
        if isinstance(data, dict):
            url = data.get("job_page_url")
    return f" Job URL: {url}" if url else ""


class ExtractionModule:
    """Extraction module — full and field extraction."""

    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        client: httpx.Client,
        timeout_s: float,
        poll_interval_s: float,
        poll_max_interval_s: float,
    ):
        self._extract = ExtractResource(base_url, token, client)
        self._tasks = TasksResource(base_url, token, client)
        self._zip = ZipResource(base_url, token, client)
        self.status = StatusResource(base_url, token, client)
        self.documents = DocumentsResource(base_url, token, client)

        self._timeout_s = timeout_s
        self._poll_interval_s = poll_interval_s
        self._poll_max_interval_s = poll_max_interval_s

    def extract(
        self,
        *,
        documents: Optional[List[Tuple[str, bytes]]] = None,
        urls: Optional[List[str]] = None,
        alias: Optional[str] = None,
        description: Optional[str] = None,
        enrichment_mode: Optional[EnrichmentMode] = None,
    ) -> Dict[str, Any]:
        return self._extract.extract(
            documents=documents,
            urls=urls,
            alias=alias,
            description=description,
            enrichment_mode=enrichment_mode,
        )

    def extract_fields(
        self,
        *,
        json_schema: Dict[str, Any],
        documents: Optional[List[Tuple[str, bytes]]] = None,
        urls: Optional[List[str]] = None,
        alias: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self._extract.extract_fields(
            json_schema=json_schema,
            documents=documents,
            urls=urls,
            alias=alias,
            description=description,
        )

    def generate_schema(self, *, description: str) -> Dict[str, Any]:
        return self._extract.generate_schema(description=description)

    def list_tasks(self) -> Dict[str, Any]:
        return self._tasks.list()

    def make_zip(
        self,
        *,
        job_uid: str,
        document_uid: Optional[str] = None,
        local_images: bool = False,
        content_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        return self._zip.make_zip(
            job_uid=job_uid,
            document_uid=document_uid,
            local_images=local_images,
            content_types=content_types,
        )

    @staticmethod
    def extract_request_uid(extract_response: Dict[str, Any]) -> str:
        """Return ``request_uid`` from an extract endpoint payload."""
        return _extract_request_uid(extract_response)

    @staticmethod
    def extract_document_ids(status_response: Dict[str, Any]) -> List[str]:
        """Return document IDs from a request-status payload."""
        return _extract_document_ids(status_response)

    def wait_for_request(
        self,
        request_uid: str,
        *,
        timeout_s: Optional[float] = None,
        poll_interval_s: Optional[float] = None,
        poll_max_interval_s: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Poll ``/request-status/{request_uid}`` until a terminal state or timeout."""
        return wait_for_terminal_status(
            fetch_status=lambda: self.status.request(request_uid),
            extract_status=extract_status,
            timeout_s=self._timeout_s if timeout_s is None else timeout_s,
            poll_interval_s=(
                self._poll_interval_s if poll_interval_s is None else poll_interval_s
            ),
            poll_max_interval_s=(
                self._poll_max_interval_s
                if poll_max_interval_s is None
                else poll_max_interval_s
            ),
            identifier=f"request {request_uid}",
            timeout_context=_extraction_timeout_suffix,
        )


class AsyncExtractionModule:
    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        client: httpx.AsyncClient,
        timeout_s: float,
        poll_interval_s: float,
        poll_max_interval_s: float,
    ):
        self._extract = AsyncExtractResource(base_url, token, client)
        self._tasks = AsyncTasksResource(base_url, token, client)
        self._zip = AsyncZipResource(base_url, token, client)
        self.status = AsyncStatusResource(base_url, token, client)
        self.documents = AsyncDocumentsResource(base_url, token, client)

        self._timeout_s = timeout_s
        self._poll_interval_s = poll_interval_s
        self._poll_max_interval_s = poll_max_interval_s

    async def extract(
        self,
        *,
        documents: Optional[List[Tuple[str, bytes]]] = None,
        urls: Optional[List[str]] = None,
        alias: Optional[str] = None,
        description: Optional[str] = None,
        enrichment_mode: Optional[EnrichmentMode] = None,
    ) -> Dict[str, Any]:
        return await self._extract.extract(
            documents=documents,
            urls=urls,
            alias=alias,
            description=description,
            enrichment_mode=enrichment_mode,
        )

    async def extract_fields(
        self,
        *,
        json_schema: Dict[str, Any],
        documents: Optional[List[Tuple[str, bytes]]] = None,
        urls: Optional[List[str]] = None,
        alias: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self._extract.extract_fields(
            json_schema=json_schema,
            documents=documents,
            urls=urls,
            alias=alias,
            description=description,
        )

    async def generate_schema(self, *, description: str) -> Dict[str, Any]:
        return await self._extract.generate_schema(description=description)

    async def list_tasks(self) -> Dict[str, Any]:
        return await self._tasks.list()

    async def make_zip(
        self,
        *,
        job_uid: str,
        document_uid: Optional[str] = None,
        local_images: bool = False,
        content_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        return await self._zip.make_zip(
            job_uid=job_uid,
            document_uid=document_uid,
            local_images=local_images,
            content_types=content_types,
        )

    @staticmethod
    def extract_request_uid(extract_response: Dict[str, Any]) -> str:
        """Return ``request_uid`` from an extract endpoint payload."""
        return _extract_request_uid(extract_response)

    @staticmethod
    def extract_document_ids(status_response: Dict[str, Any]) -> List[str]:
        """Return document IDs from a request-status payload."""
        return _extract_document_ids(status_response)

    async def wait_for_request(
        self,
        request_uid: str,
        *,
        timeout_s: Optional[float] = None,
        poll_interval_s: Optional[float] = None,
        poll_max_interval_s: Optional[float] = None,
    ) -> Dict[str, Any]:
        async def _fetch() -> Dict[str, Any]:
            return await self.status.request(request_uid)

        return await wait_for_terminal_status_async(
            fetch_status=_fetch,
            extract_status=extract_status,
            timeout_s=self._timeout_s if timeout_s is None else timeout_s,
            poll_interval_s=(
                self._poll_interval_s if poll_interval_s is None else poll_interval_s
            ),
            poll_max_interval_s=(
                self._poll_max_interval_s
                if poll_max_interval_s is None
                else poll_max_interval_s
            ),
            identifier=f"request {request_uid}",
            timeout_context=_extraction_timeout_suffix,
        )


class ChunkingModule:
    """Chunking module — job submission, analysis, signed-URL results."""

    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        client: httpx.Client,
        timeout_s: float,
        poll_interval_s: float,
        poll_max_interval_s: float,
    ):
        self.jobs = ChunkingJobsResource(
            base_url,
            token,
            client,
            timeout_s=timeout_s,
            poll_interval_s=poll_interval_s,
            poll_max_interval_s=poll_max_interval_s,
        )
        self._analyze = AnalyzeResource(base_url, token, client)
        self._results = ResultsResource(base_url, token, client)

    def analyze(self, bucket_uid: str) -> Dict[str, Any]:
        """POST /v1/chunk/analyze.

        Generates statistics and a distribution plot, returns a `ResultsResponse`
        whose ``result.files`` maps the filenames (`chunking_statistics.json`,
        `chunking_distribution.png`) to short-lived signed URLs.
        """
        return self._analyze.analyze(bucket_uid)

    def results(self, bucket_uid: str) -> Dict[str, bytes]:
        """POST /v1/chunk/results then fetch each signed URL.

        Returns ``{filename: bytes}``. File bytes transit directly between the
        client and the storage backend, not through the API server.
        """
        return self._results.results(bucket_uid)


class AsyncChunkingModule:
    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        client: httpx.AsyncClient,
        timeout_s: float,
        poll_interval_s: float,
        poll_max_interval_s: float,
    ):
        self.jobs = AsyncChunkingJobsResource(
            base_url,
            token,
            client,
            timeout_s=timeout_s,
            poll_interval_s=poll_interval_s,
            poll_max_interval_s=poll_max_interval_s,
        )
        self._analyze = AsyncAnalyzeResource(base_url, token, client)
        self._results = AsyncResultsResource(base_url, token, client)

    async def analyze(self, bucket_uid: str) -> Dict[str, Any]:
        return await self._analyze.analyze(bucket_uid)

    async def results(self, bucket_uid: str) -> Dict[str, bytes]:
        return await self._results.results(bucket_uid)


class EmbeddingModule:
    """Embedding module — job submission, model listing, signed-URL results."""

    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        client: httpx.Client,
        timeout_s: float,
        poll_interval_s: float,
        poll_max_interval_s: float,
    ):
        self.jobs = EmbeddingJobsResource(
            base_url,
            token,
            client,
            timeout_s=timeout_s,
            poll_interval_s=poll_interval_s,
            poll_max_interval_s=poll_max_interval_s,
        )
        self._models = EmbeddingModelsResource(base_url, token, client)
        self._results = EmbeddingResultsResource(base_url, token, client)

    def list_models(self) -> Dict[str, Any]:
        """GET /v1/embed/models — list internal embedding models."""
        return self._models.list()

    def results(self, bucket_uid: str) -> Dict[str, bytes]:
        """POST /v1/embed/results then fetch each signed URL.

        Returns ``{filename: bytes}``. File bytes transit directly between the
        client and the storage backend, not through the API server.
        """
        return self._results.results(bucket_uid)


class AsyncEmbeddingModule:
    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        client: httpx.AsyncClient,
        timeout_s: float,
        poll_interval_s: float,
        poll_max_interval_s: float,
    ):
        self.jobs = AsyncEmbeddingJobsResource(
            base_url,
            token,
            client,
            timeout_s=timeout_s,
            poll_interval_s=poll_interval_s,
            poll_max_interval_s=poll_max_interval_s,
        )
        self._models = AsyncEmbeddingModelsResource(base_url, token, client)
        self._results = AsyncEmbeddingResultsResource(base_url, token, client)

    async def list_models(self) -> Dict[str, Any]:
        return await self._models.list()

    async def results(self, bucket_uid: str) -> Dict[str, bytes]:
        return await self._results.results(bucket_uid)


class ManagementModule:
    """Management module — bucket CRUD."""

    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        client: httpx.Client,
    ):
        self.buckets = BucketsResource(base_url, token, client)


class AsyncManagementModule:
    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        client: httpx.AsyncClient,
    ):
        self.buckets = AsyncBucketsResource(base_url, token, client)


class VectorStoreModule:
    """Vector Store module — collection creation and async vector-load jobs."""

    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        client: httpx.Client,
        timeout_s: float,
        poll_interval_s: float,
        poll_max_interval_s: float,
    ):
        self.collections = VectorStoreCollectionsResource(base_url, token, client)
        self.jobs = VectorStoreJobsResource(
            base_url,
            token,
            client,
            timeout_s=timeout_s,
            poll_interval_s=poll_interval_s,
            poll_max_interval_s=poll_max_interval_s,
        )


class AsyncVectorStoreModule:
    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        client: httpx.AsyncClient,
        timeout_s: float,
        poll_interval_s: float,
        poll_max_interval_s: float,
    ):
        self.collections = AsyncVectorStoreCollectionsResource(base_url, token, client)
        self.jobs = AsyncVectorStoreJobsResource(
            base_url,
            token,
            client,
            timeout_s=timeout_s,
            poll_interval_s=poll_interval_s,
            poll_max_interval_s=poll_max_interval_s,
        )


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
