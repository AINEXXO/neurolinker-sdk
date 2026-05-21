from __future__ import annotations

import pytest

from neurolinker_sdk import AsyncNeuroLinker, NeuroLinker
from neurolinker_sdk.config import (
    DEFAULT_POLL_INTERVAL_S,
    DEFAULT_POLL_MAX_INTERVAL_S,
    DEFAULT_TIMEOUT_S,
)

# ---------------------------------------------------------------------------
# Module surface — the 5 modules must be reachable on both clients
# ---------------------------------------------------------------------------


def test_sync_client_exposes_all_modules() -> None:
    with NeuroLinker(token="nl_dummy", timeout_s=1.0) as client:
        assert hasattr(client, "extraction")
        assert hasattr(client, "chunking")
        assert hasattr(client, "embedding")
        assert hasattr(client, "management")
        assert hasattr(client, "vector_store")


@pytest.mark.asyncio
async def test_async_client_exposes_all_modules() -> None:
    async with AsyncNeuroLinker(token="nl_dummy", timeout_s=1.0) as client:
        assert hasattr(client, "extraction")
        assert hasattr(client, "chunking")
        assert hasattr(client, "embedding")
        assert hasattr(client, "management")
        assert hasattr(client, "vector_store")


# ---------------------------------------------------------------------------
# Default poll params — propagated when no override
# ---------------------------------------------------------------------------


def test_sync_default_poll_params_propagate_to_all_polling_modules() -> None:
    with NeuroLinker(token="nl_dummy") as client:
        # extraction module owns the params directly
        assert client.extraction._timeout_s == DEFAULT_TIMEOUT_S
        assert client.extraction._poll_interval_s == DEFAULT_POLL_INTERVAL_S
        assert client.extraction._poll_max_interval_s == DEFAULT_POLL_MAX_INTERVAL_S

        # JobsResource carries its own copy of poll params per module
        for jobs in (
            client.chunking.jobs,
            client.embedding.jobs,
            client.vector_store.jobs,
        ):
            assert jobs._timeout_s == DEFAULT_TIMEOUT_S
            assert jobs._poll_interval_s == DEFAULT_POLL_INTERVAL_S
            assert jobs._poll_max_interval_s == DEFAULT_POLL_MAX_INTERVAL_S


@pytest.mark.asyncio
async def test_async_default_poll_params_propagate_to_all_polling_modules() -> None:
    async with AsyncNeuroLinker(token="nl_dummy") as client:
        assert client.extraction._timeout_s == DEFAULT_TIMEOUT_S
        assert client.extraction._poll_interval_s == DEFAULT_POLL_INTERVAL_S
        assert client.extraction._poll_max_interval_s == DEFAULT_POLL_MAX_INTERVAL_S

        for jobs in (
            client.chunking.jobs,
            client.embedding.jobs,
            client.vector_store.jobs,
        ):
            assert jobs._timeout_s == DEFAULT_TIMEOUT_S
            assert jobs._poll_interval_s == DEFAULT_POLL_INTERVAL_S
            assert jobs._poll_max_interval_s == DEFAULT_POLL_MAX_INTERVAL_S


# ---------------------------------------------------------------------------
# Custom poll params — propagated to every polling module
# ---------------------------------------------------------------------------


def test_sync_custom_poll_params_propagate_to_all_polling_modules() -> None:
    with NeuroLinker(
        token="nl_dummy",
        timeout_s=900.0,
        poll_interval_s=1.0,
        poll_max_interval_s=6.0,
    ) as client:
        assert client.extraction._timeout_s == 900.0
        assert client.extraction._poll_interval_s == 1.0
        assert client.extraction._poll_max_interval_s == 6.0

        for jobs in (
            client.chunking.jobs,
            client.embedding.jobs,
            client.vector_store.jobs,
        ):
            assert jobs._timeout_s == 900.0
            assert jobs._poll_interval_s == 1.0
            assert jobs._poll_max_interval_s == 6.0


@pytest.mark.asyncio
async def test_async_custom_poll_params_propagate_to_all_polling_modules() -> None:
    async with AsyncNeuroLinker(
        token="nl_dummy",
        timeout_s=900.0,
        poll_interval_s=1.0,
        poll_max_interval_s=6.0,
    ) as client:
        assert client.extraction._timeout_s == 900.0
        assert client.extraction._poll_interval_s == 1.0
        assert client.extraction._poll_max_interval_s == 6.0

        for jobs in (
            client.chunking.jobs,
            client.embedding.jobs,
            client.vector_store.jobs,
        ):
            assert jobs._timeout_s == 900.0
            assert jobs._poll_interval_s == 1.0
            assert jobs._poll_max_interval_s == 6.0


# ---------------------------------------------------------------------------
# Custom base_url propagation
# ---------------------------------------------------------------------------


def test_sync_custom_base_url_strips_trailing_slash() -> None:
    with NeuroLinker(
        token="nl_dummy",
        base_url="https://staging.example.com/",
        timeout_s=1.0,
    ) as client:
        assert client._base_url == "https://staging.example.com"


@pytest.mark.asyncio
async def test_async_custom_base_url_strips_trailing_slash() -> None:
    async with AsyncNeuroLinker(
        token="nl_dummy",
        base_url="https://staging.example.com/",
        timeout_s=1.0,
    ) as client:
        assert client._base_url == "https://staging.example.com"
