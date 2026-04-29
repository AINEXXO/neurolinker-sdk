from __future__ import annotations

import json
from typing import Any, Dict

import httpx

from ..errors import NeuroLinkerAPIError, NeuroLinkerConfigError
from ..http import _build_url, _json_headers, _raise_for_status


_REDACTED = "[REDACTED]"


def _redact_secret_in_error(
    exc: NeuroLinkerAPIError, secret_value: str
) -> NeuroLinkerAPIError:
    """Return a copy of ``exc`` with occurrences of ``secret_value`` masked.

    Defensive: the backend should never echo the value, but if it does we strip
    it from ``response_text`` and ``response_json`` before re-raising.
    """
    if not secret_value:
        return exc

    redacted_text = exc.response_text.replace(secret_value, _REDACTED)

    redacted_json = exc.response_json
    if redacted_json is not None:
        try:
            redacted_json = json.loads(
                json.dumps(redacted_json).replace(secret_value, _REDACTED)
            )
        except (TypeError, ValueError):
            redacted_json = exc.response_json

    return NeuroLinkerAPIError(
        status_code=exc.status_code,
        method=exc.method,
        url=exc.url,
        response_text=redacted_text,
        response_json=redacted_json,
    )


class SecretsResource:
    def __init__(self, base_url: str, token: str, client: httpx.Client):
        self._base_url = base_url
        self._token = token
        self._client = client

    def create(self, *, name: str, value: str) -> Dict[str, Any]:
        """POST /v1/management/secrets"""
        if not name:
            raise NeuroLinkerConfigError("name must be a non-empty string.")
        if not value:
            raise NeuroLinkerConfigError("value must be a non-empty string.")

        resp = self._client.post(
            _build_url(self._base_url, "/v1/management/secrets"),
            json={"name": name, "value": value},
            headers=_json_headers(self._token),
        )
        try:
            _raise_for_status(resp)
        except NeuroLinkerAPIError as exc:
            raise _redact_secret_in_error(exc, value) from None
        return resp.json()

    def list(self) -> Dict[str, Any]:
        """GET /v1/management/secrets"""
        resp = self._client.get(
            _build_url(self._base_url, "/v1/management/secrets"),
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        return resp.json()

    def update(self, secret_id: str, *, value: str) -> None:
        """PUT /v1/management/secrets/{secret_id}"""
        if not secret_id:
            raise NeuroLinkerConfigError("secret_id must be a non-empty string.")
        if not value:
            raise NeuroLinkerConfigError("value must be a non-empty string.")

        resp = self._client.put(
            _build_url(self._base_url, f"/v1/management/secrets/{secret_id}"),
            json={"value": value},
            headers=_json_headers(self._token),
        )
        try:
            _raise_for_status(resp)
        except NeuroLinkerAPIError as exc:
            raise _redact_secret_in_error(exc, value) from None
        return None

    def delete(self, secret_id: str) -> None:
        """DELETE /v1/management/secrets/{secret_id}"""
        if not secret_id:
            raise NeuroLinkerConfigError("secret_id must be a non-empty string.")

        resp = self._client.delete(
            _build_url(self._base_url, f"/v1/management/secrets/{secret_id}"),
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        return None


class AsyncSecretsResource:
    def __init__(self, base_url: str, token: str, client: httpx.AsyncClient):
        self._base_url = base_url
        self._token = token
        self._client = client

    async def create(self, *, name: str, value: str) -> Dict[str, Any]:
        if not name:
            raise NeuroLinkerConfigError("name must be a non-empty string.")
        if not value:
            raise NeuroLinkerConfigError("value must be a non-empty string.")

        resp = await self._client.post(
            _build_url(self._base_url, "/v1/management/secrets"),
            json={"name": name, "value": value},
            headers=_json_headers(self._token),
        )
        try:
            _raise_for_status(resp)
        except NeuroLinkerAPIError as exc:
            raise _redact_secret_in_error(exc, value) from None
        return resp.json()

    async def list(self) -> Dict[str, Any]:
        resp = await self._client.get(
            _build_url(self._base_url, "/v1/management/secrets"),
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        return resp.json()

    async def update(self, secret_id: str, *, value: str) -> None:
        if not secret_id:
            raise NeuroLinkerConfigError("secret_id must be a non-empty string.")
        if not value:
            raise NeuroLinkerConfigError("value must be a non-empty string.")

        resp = await self._client.put(
            _build_url(self._base_url, f"/v1/management/secrets/{secret_id}"),
            json={"value": value},
            headers=_json_headers(self._token),
        )
        try:
            _raise_for_status(resp)
        except NeuroLinkerAPIError as exc:
            raise _redact_secret_in_error(exc, value) from None
        return None

    async def delete(self, secret_id: str) -> None:
        if not secret_id:
            raise NeuroLinkerConfigError("secret_id must be a non-empty string.")

        resp = await self._client.delete(
            _build_url(self._base_url, f"/v1/management/secrets/{secret_id}"),
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        return None
