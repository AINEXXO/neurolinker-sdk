import os

import pytest

from neurolinker_sdk import AsyncNeuroLinker, ContentType, NeuroLinker

from test_e2e_api_async import (
    _extract_request_uid as _extract_request_uid_async,
    _extract_document_ids_from_request_status,
    _wait_for_request_completion as _wait_for_request_completion_async,
)
from test_e2e_api_sync_local import (
    _extract_request_uid as _extract_request_uid_sync,
    _wait_for_request_completion as _wait_for_request_completion_sync,
)
from test_e2e_api_sync import _assert_documents_results_schema


TOKEN = os.getenv("NEUROLINKER_API_KEY")
PDF_URL = os.getenv("NEUROLINKER_TEST_PDF_URL")

E2E_TIMEOUT_S = float(os.getenv("NEUROLINKER_E2E_TIMEOUT_S", "1800"))


pytestmark = pytest.mark.skipif(
    not TOKEN or not PDF_URL,
    reason="Set NEUROLINKER_API_KEY and NEUROLINKER_TEST_PDF_URL to run URL E2E tests.",
)


@pytest.mark.asyncio
async def test_documents_content_types_async() -> None:
    """E2E test for the content_types filter on markdown/json endpoints (async client).

    The goal is to verify that the backend accepts the new content_types parameter
    and returns a valid DocumentResultResponse for each content class.
    """
    async with AsyncNeuroLinker.from_env(timeout_s=E2E_TIMEOUT_S) as client:
        # Submit an extract job for a remote PDF URL.
        extract_resp = await client.extraction.extract(
            urls=[PDF_URL],
            alias="sdk-e2e-content-types-async",
        )
        request_uid = _extract_request_uid_async(extract_resp)

        # Wait for completion and obtain document ids.
        status_resp = await _wait_for_request_completion_async(client, request_uid)
        doc_ids = _extract_document_ids_from_request_status(status_resp)
        assert doc_ids, f"Expected at least one document id in status: {status_resp}"

        # Check that each content type is accepted for markdown/json.
        for ct in (ContentType.TEXT, ContentType.FORMULA, ContentType.TABLES, ContentType.IMAGES):
            md = await client.extraction.documents.markdown(doc_ids, content_types=[ct])
            _assert_documents_results_schema(md)

            js = await client.extraction.documents.json(doc_ids, content_types=[ct])
            _assert_documents_results_schema(js)


def test_documents_content_types_sync() -> None:
    """E2E test for the content_types filter on markdown/json endpoints (sync client).

    This mirrors the async test but uses the synchronous NeuroLinker client.
    """
    with NeuroLinker.from_env(timeout_s=E2E_TIMEOUT_S) as client:
        # Submit an extract job for a remote PDF URL.
        extract_resp = client.extraction.extract(
            urls=[PDF_URL],
            alias="sdk-e2e-content-types-sync",
        )
        request_uid = _extract_request_uid_sync(extract_resp)

        # Wait for completion and obtain document ids.
        status_resp = _wait_for_request_completion_sync(client, request_uid)
        doc_ids = _extract_document_ids_from_request_status(status_resp)
        assert doc_ids, f"Expected at least one document id in status: {status_resp}"

        for ct in (ContentType.TEXT, ContentType.FORMULA, ContentType.TABLES, ContentType.IMAGES):
            md = client.extraction.documents.markdown(doc_ids, content_types=[ct])
            _assert_documents_results_schema(md)

            js = client.extraction.documents.json(doc_ids, content_types=[ct])
            _assert_documents_results_schema(js)
