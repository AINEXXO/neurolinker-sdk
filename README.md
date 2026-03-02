# neurolinker-sdk
A Python SDK for the NeuroLinker API from Ainexxo S.R.L. The SDK provides sync and async clients to submit documents, track extraction jobs, and retrieve processed results.

**Download**

```bash
pip install neurolinker-sdk
```

**Initial Setup**

The steps below are for contributors or anyone running tests locally.

```bash
python -m venv .venv
source .venv/bin/activate
```

```bash
pip install -e ".[dev]"
```

Optional formatting and linting (as used in this repo):

```bash
uv run ruff format .
uv run ruff check .
```

Run tests:

```bash
uv run pytest
```

**Usage**

Set credentials preferably into a .env file (token is required; NEUROLINKER_BASE_URL is optional and defaults to the public deployment).

`NEUROLINKER_TOKEN` (required) : generate it from the official neurolinker website https://neurolinker.ainexxo.com/ - Login and go to the API KEY section.

```bash
export NEUROLINKER_TOKEN="your_token"
export NEUROLINKER_BASE_URL="https://neurolinker.api.ainexxo.com"
```

Quick start (**sync**):

```python
from neurolinker_sdk import NeuroLinker

with NeuroLinker.from_env() as client:
    tasks = client.tasks.list()
```

Quick start (**async**):

```python
from neurolinker_sdk import AsyncNeuroLinker

async with AsyncNeuroLinker.from_env() as client:
    tasks = await client.tasks.list()
```

 SDK functionality (minimal usage + parameters).
 These are the ways to define a client before it get used.

- `NeuroLinker(base_url, token, timeout_s=30.0, http_client=None)`
Minimal sync client constructor. Provide a base URL and token, optionally a custom `httpx.Client`.

- `NeuroLinker.from_env(timeout_s=30.0)`
Loads `NEUROLINKER_TOKEN` and optional `NEUROLINKER_BASE_URL` from the environment.

- `AsyncNeuroLinker(base_url, token, timeout_s=30.0, http_client=None)`
Minimal async client constructor. Provide a base URL and token, optionally a custom `httpx.AsyncClient`.

- `AsyncNeuroLinker.from_env(timeout_s=30.0)`
Async version of `from_env`.

These are a list of methods that can be used. Async equivalents exist for every resource and use the same parameters with `await`.

- `client.tasks.list()`
List the processing tasks available in the system.

- `client.extract.extract(documents=[("file.pdf", b"...")], urls=None, alias=None, description=None)`
Upload PDFs from bytes. `documents` and `urls` are mutually exclusive.

- `client.extract.extract(documents=None, urls=["https://..."], alias="optional", description="optional")`
Submit a URL-based extraction job.

- `client.status.request(request_id)`
Check the status of an extraction request by request ID.

- `client.status.document(document_id)`
Check the status of a single document by document ID.

- `client.documents.markdown(document_ids, content_types=None)`
Retrieve markdown results for document IDs. `content_types` can be a list of `ContentType` values or strings.

- `client.documents.json(document_ids, content_types=None)`
Retrieve JSON results for document IDs, with optional content type filtering.

- `client.documents.images(document_ids)`
Retrieve extracted image metadata for document IDs.

- `client.documents.page_summaries(document_ids)`
Retrieve per-page summaries.

- `client.documents.summary(document_ids)`
Retrieve a document-level summary.

- `client.documents.section_summaries(document_ids)`
Retrieve summaries grouped by detected sections.

- `client.documents.section_summary(document_ids)`
Retrieve a single consolidated section summary.

- `from neurolinker_sdk.resources.documents import ContentType`
Use `ContentType.TEXT`, `ContentType.FORMULA`, `ContentType.TABLES`, `ContentType.IMAGES` to filter content returned by markdown/json endpoints.

- `client.zip.make_zip(job_uid, document_uid=None, local_images=False)`
Request a ZIP archive for a completed extraction job (entire job or a single document). If `local_images=True` then the images will be stored locally.


- `NeuroLinkerAPIError`, `NeuroLinkerConfigError`
Exceptions raised for non-2xx API responses or missing/invalid configuration.

Tests in this repository cover sync and async flows, URL-based extraction, local file uploads, section endpoints, content type filters, and ZIP creation. See the `tests/` directory. The E2E tests use these environment variables:

- `NEUROLINKER_TOKEN` (required) : generate it from the official neurolinker website https://neurolinker.ainexxo.com/ - login and go to the API KEY section.
- `NEUROLINKER_TEST_PDF_URL` (required for URL-based E2E) : Its a web url of a pdf that can be downloaded from the backend.
Example: "https://arxiv.org/pdf/..." 
- `NEUROLINKER_TEST_PDF_PATH` or `NEUROLINKER_TEST_PDF_PATHS` (required for local upload E2E); Its the local path of a pdf. Example: "<local_path>/mypdf1.pdf" and "<local_path>/mypdf2.pdf,<local_path>/mypdf3.pdf"
- `NEUROLINKER_E2E_TIMEOUT_S`, `NEUROLINKER_E2E_POLL_INTERVAL_S`, `NEUROLINKER_E2E_POLL_MAX_INTERVAL_S` (optional): which are respectively set to 900 (adjust until your file has completed), 2, 10. 
