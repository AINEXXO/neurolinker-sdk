from __future__ import annotations

from typing import Any, Dict

import httpx

from ...errors import NeuroLinkerConfigError
from ...http import _build_url, _json_headers, _raise_for_status


class TracksResource:
    """Track CRUD: a track is a long-lived container for continuous evaluation of
    a production RAG."""

    def __init__(self, base_url: str, token: str, client: httpx.Client):
        self._base_url = base_url
        self._token = token
        self._client = client

    def create(self, *, name: str) -> Dict[str, Any]:
        """POST /v1/eval/tracks — create a track. Returns the body carrying
        ``track_uid`` (keep it: it's what you pass to ``instrument``)."""
        if not name:
            raise NeuroLinkerConfigError("name must be a non-empty string.")
        resp = self._client.post(
            _build_url(self._base_url, "/v1/eval/tracks"),
            json={"name": name},
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        return resp.json()

    def list(self) -> Dict[str, Any]:
        """GET /v1/eval/tracks — all the caller's tracks (active + disabled), each
        carrying its ``active`` flag."""
        resp = self._client.get(
            _build_url(self._base_url, "/v1/eval/tracks"),
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        return resp.json()

    def set_active(self, track_uid: str, *, active: bool) -> Dict[str, Any]:
        """PATCH /v1/eval/tracks/{track_uid} — enable/disable a track. While
        disabled, ingest refuses its traces and the evaluator skips it; the
        historical records stay readable."""
        if not track_uid:
            raise NeuroLinkerConfigError("track_uid must be a non-empty string.")
        resp = self._client.patch(
            _build_url(self._base_url, f"/v1/eval/tracks/{track_uid}"),
            json={"active": active},
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        return resp.json()


class AsyncTracksResource:
    """Async twin of :class:`TracksResource`."""

    def __init__(self, base_url: str, token: str, client: httpx.AsyncClient):
        self._base_url = base_url
        self._token = token
        self._client = client

    async def create(self, *, name: str) -> Dict[str, Any]:
        if not name:
            raise NeuroLinkerConfigError("name must be a non-empty string.")
        resp = await self._client.post(
            _build_url(self._base_url, "/v1/eval/tracks"),
            json={"name": name},
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        return resp.json()

    async def list(self) -> Dict[str, Any]:
        resp = await self._client.get(
            _build_url(self._base_url, "/v1/eval/tracks"),
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        return resp.json()

    async def set_active(self, track_uid: str, *, active: bool) -> Dict[str, Any]:
        if not track_uid:
            raise NeuroLinkerConfigError("track_uid must be a non-empty string.")
        resp = await self._client.patch(
            _build_url(self._base_url, f"/v1/eval/tracks/{track_uid}"),
            json={"active": active},
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        return resp.json()


class QueriesResource:
    """Read the curated per-query records (input/output, contexts, metrics) a
    track has accumulated — the dashboard's data, from Firestore."""

    def __init__(self, base_url: str, token: str, client: httpx.Client):
        self._base_url = base_url
        self._token = token
        self._client = client

    def list(self, track_uid: str, *, limit: int = 100) -> Dict[str, Any]:
        """GET /v1/eval/tracks/{track_uid}/queries — per-query rows, most recent
        first."""
        if not track_uid:
            raise NeuroLinkerConfigError("track_uid must be a non-empty string.")
        resp = self._client.get(
            _build_url(self._base_url, f"/v1/eval/tracks/{track_uid}/queries"),
            params={"limit": limit},
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        return resp.json()

    def get(self, track_uid: str, trace_id: str) -> Dict[str, Any]:
        """GET /v1/eval/tracks/{track_uid}/queries/{trace_id} — drill-down for one
        query."""
        if not track_uid or not trace_id:
            raise NeuroLinkerConfigError("track_uid and trace_id must be non-empty.")
        resp = self._client.get(
            _build_url(self._base_url, f"/v1/eval/tracks/{track_uid}/queries/{trace_id}"),
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        return resp.json()


class AsyncQueriesResource:
    """Async twin of :class:`QueriesResource`."""

    def __init__(self, base_url: str, token: str, client: httpx.AsyncClient):
        self._base_url = base_url
        self._token = token
        self._client = client

    async def list(self, track_uid: str, *, limit: int = 100) -> Dict[str, Any]:
        if not track_uid:
            raise NeuroLinkerConfigError("track_uid must be a non-empty string.")
        resp = await self._client.get(
            _build_url(self._base_url, f"/v1/eval/tracks/{track_uid}/queries"),
            params={"limit": limit},
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        return resp.json()

    async def get(self, track_uid: str, trace_id: str) -> Dict[str, Any]:
        if not track_uid or not trace_id:
            raise NeuroLinkerConfigError("track_uid and trace_id must be non-empty.")
        resp = await self._client.get(
            _build_url(self._base_url, f"/v1/eval/tracks/{track_uid}/queries/{trace_id}"),
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        return resp.json()
