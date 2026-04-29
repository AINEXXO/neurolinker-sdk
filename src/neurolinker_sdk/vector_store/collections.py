from __future__ import annotations

from typing import Any, Dict, Union

import httpx

from ..validation import normalize_pydantic
from ..http import _build_url, _json_headers, _raise_for_status
from .models import CollectionSchema, VectorDBConfig


def _build_create_payload(
    collection: Union[CollectionSchema, Dict[str, Any]],
    vector_db_config: Union[VectorDBConfig, Dict[str, Any]],
    database: str,
) -> Dict[str, Any]:
    return {
        "collection": normalize_pydantic(
            collection, CollectionSchema, label="collection"
        ),
        "vector_db_config": normalize_pydantic(
            vector_db_config, VectorDBConfig, label="vector_db_config"
        ),
        "database": database or "",
    }


class CollectionsResource:
    def __init__(self, base_url: str, token: str, client: httpx.Client):
        self._base_url = base_url
        self._token = token
        self._client = client

    def create(
        self,
        *,
        collection: Union[CollectionSchema, Dict[str, Any]],
        vector_db_config: Union[VectorDBConfig, Dict[str, Any]],
        database: str = "",
    ) -> Dict[str, Any]:
        """POST /v1/vector-store/collections (synchronous operation).

        Idempotent: creating an existing collection returns success with
        ``already_existed=true``.
        """
        payload = _build_create_payload(collection, vector_db_config, database)
        resp = self._client.post(
            _build_url(self._base_url, "/v1/vector-store/collections"),
            json=payload,
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        return resp.json()


class AsyncCollectionsResource:
    def __init__(self, base_url: str, token: str, client: httpx.AsyncClient):
        self._base_url = base_url
        self._token = token
        self._client = client

    async def create(
        self,
        *,
        collection: Union[CollectionSchema, Dict[str, Any]],
        vector_db_config: Union[VectorDBConfig, Dict[str, Any]],
        database: str = "",
    ) -> Dict[str, Any]:
        payload = _build_create_payload(collection, vector_db_config, database)
        resp = await self._client.post(
            _build_url(self._base_url, "/v1/vector-store/collections"),
            json=payload,
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        return resp.json()
