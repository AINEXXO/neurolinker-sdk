import os

import pytest

from neurolinker_sdk import AsyncNeuroLinker

from test_e2e_api_sync import (
    _extract_request_uid,
    _extract_document_ids_from_request_status,
    _wait_for_request_completion,
    _assert_documents_results_schema,
)

TOKEN = os.getenv("NEUROLINKER_TOKEN")
PDF_URL = os.getenv("NEUROLINKER_TEST_PDF_URL")

E2E_TIMEOUT_S = float(os.getenv("NEUROLINKER_E2E_TIMEOUT_S", "600"))

pytestmark = pytest.mark.skipif(
    not TOKEN or not PDF_URL,
    reason="Set NEUROLINKER_TOKEN and NEUROLINKER_TEST_PDF_URL to run URL E2E tests.",
)


@pytest.mark.asyncio
async def test_section_results_endpoints() -> None:
    """
    E2E check for the section-based result endpoints:

      - POST /documents/section-summaries
      - POST /documents/section-summary

    These behave like page-summaries/summary but operate at section granularity.
    """
    async with AsyncNeuroLinker.from_env(timeout_s=E2E_TIMEOUT_S) as client:
        # Submit extract request.
        extract_resp = await client.extract.extract(
            urls=[PDF_URL],
            alias="sdk-e2e-sections",
        )
        request_uid = _extract_request_uid(extract_resp)

        # Wait for completion and get document ids.
        status_resp = await _wait_for_request_completion(client, request_uid)
        doc_ids = _extract_document_ids_from_request_status(status_resp)
        assert doc_ids, f"Expected at least one document id in status: {status_resp}"

        # Call the new section endpoints and use the same schema checks as existing tests.
        res_section_summaries = await client.documents.section_summaries(doc_ids)
        _assert_documents_results_schema(res_section_summaries)

        res_section_summary = await client.documents.section_summary(doc_ids)
        _assert_documents_results_schema(res_section_summary)