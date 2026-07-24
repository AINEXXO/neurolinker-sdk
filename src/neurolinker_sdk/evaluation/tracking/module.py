from __future__ import annotations

from typing import Any, Dict

import httpx

from .tracks import (
    AsyncQueriesResource,
    AsyncTracksResource,
    QueriesResource,
    TracksResource,
)


class TrackingModule:
    """Tracking module — track CRUD (`.tracks`) + dashboard reads of the curated
    per-query records (`.queries` / `.query`). To attach the tracer to a RAG app,
    use the top-level `neurolinker_sdk.instrument(track_uid=...)`."""

    def __init__(self, *, base_url: str, token: str, client: httpx.Client):
        self.tracks = TracksResource(base_url, token, client)
        self._queries = QueriesResource(base_url, token, client)

    def queries(self, track_uid: str, *, limit: int = 100) -> Dict[str, Any]:
        """Per-query rows a track has accumulated, most recent first."""
        return self._queries.list(track_uid, limit=limit)

    def query(self, track_uid: str, trace_id: str) -> Dict[str, Any]:
        """Drill-down for a single evaluated query."""
        return self._queries.get(track_uid, trace_id)


class AsyncTrackingModule:
    def __init__(self, *, base_url: str, token: str, client: httpx.AsyncClient):
        self.tracks = AsyncTracksResource(base_url, token, client)
        self._queries = AsyncQueriesResource(base_url, token, client)

    async def queries(self, track_uid: str, *, limit: int = 100) -> Dict[str, Any]:
        return await self._queries.list(track_uid, limit=limit)

    async def query(self, track_uid: str, trace_id: str) -> Dict[str, Any]:
        return await self._queries.get(track_uid, trace_id)
