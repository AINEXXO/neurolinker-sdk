import os
import pytest

from neurolinker_sdk import AsyncNeuroLinker

from test_e2e_api_sync import (
    _extract_request_uid,
    _extract_document_ids_from_request_status,
    _wait_for_request_completion,
    _assert_documents_results_schema,
)

TOKEN = os.getenv("NEUROLINKER_API_KEY")
PDF_URL = os.getenv("NEUROLINKER_TEST_PDF_URL")
NEUROLINKER_BASE_URL = os.getenv("NEUROLINKER_BASE_URL")
E2E_TIMEOUT_S = float(os.getenv("NEUROLINKER_E2E_TIMEOUT_S", "600"))

pytestmark = pytest.mark.skipif(
    not TOKEN or not PDF_URL,
    reason="Set NEUROLINKER_API_KEY and NEUROLINKER_TEST_PDF_URL to run URL E2E tests.",
)


@pytest.mark.asyncio
async def test_documents_summary_endpoints() -> None:
    async with AsyncNeuroLinker(token=TOKEN, base_url=NEUROLINKER_BASE_URL).from_env(timeout_s=E2E_TIMEOUT_S) as client:
        extract_resp = await client.extraction.extract(
            urls=[PDF_URL],
            alias="sdk-e2e-doc-summaries",
        )
        request_uid = _extract_request_uid(extract_resp)

        status_resp = await _wait_for_request_completion(client, request_uid)
        doc_ids = _extract_document_ids_from_request_status(status_resp)
        assert doc_ids, f"Expected at least one document id in status: {status_resp}"

        res_page_summaries = await client.extraction.documents.page_summaries(doc_ids)
        _assert_documents_results_schema(res_page_summaries)

        # document-summary now REQUIRES summary_type
        res_document_summary_page = await client.extraction.documents.document_summary(
            doc_ids, summary_type="page"
        )
        _assert_documents_results_schema(res_document_summary_page)

        res_section_summaries = await client.extraction.documents.section_summaries(doc_ids)
        _assert_documents_results_schema(res_section_summaries)

        # Optional: also verify section-type single summary
        res_document_summary_section = await client.extraction.documents.document_summary(
            doc_ids, summary_type="section"
        )
        _assert_documents_results_schema(res_document_summary_section)