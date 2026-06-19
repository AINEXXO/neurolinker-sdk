import json
import os

import pytest

from neurolinker_sdk import AsyncNeuroLinker, NeuroLinker

TOKEN = os.getenv("NEUROLINKER_API_KEY")

pytestmark = pytest.mark.skipif(
    not TOKEN,
    reason="Set NEUROLINKER_API_KEY to run this E2E test.",
)

# Inline dataset (the upload is self-contained — no bucket needed). All four
# columns present → the full metric set fires.
_ROWS = [
    {
        "user_input": "What is the capital of France?",
        "response": "The capital of France is Paris.",
        "retrieved_contexts": ["Paris is the capital and largest city of France."],
        "reference": "Paris is the capital of France.",
    },
    {
        "user_input": "What does Neurolinker do?",
        "response": "It turns raw PDFs into searchable vectors.",
        "retrieved_contexts": ["Neurolinker turns raw PDFs into searchable vectors for RAG."],
        "reference": "Neurolinker converts PDFs into vectors for retrieval-augmented generation.",
    },
]


def _jsonl() -> bytes:
    return "\n".join(json.dumps(r) for r in _ROWS).encode("utf-8")


def test_e2e_evaluation_full_flow_sync() -> None:
    """Sync end-to-end one-shot flow:
    1) upload a JSONL dataset + enqueue
    2) wait until completed
    3) fetch the parsed result.json (per-row scores + summary)
    """
    with NeuroLinker.from_env() as client:
        job = client.evaluation.oneshot.jobs.create(dataset=("e2e.jsonl", _jsonl()))
        eval_uid = job.get("eval_uid")
        assert isinstance(eval_uid, str) and eval_uid, f"missing eval_uid: {job}"
        print(f"[evaluation e2e] eval_uid={eval_uid}")

        final = client.evaluation.oneshot.jobs.wait(eval_uid)
        assert final.get("status") == "completed", f"job not completed: {final}"

        result = client.evaluation.oneshot.results(eval_uid)
        assert result.get("rows"), f"no per-row results: {result}"
        assert result.get("summary"), f"no summary: {result}"
        assert len(result["rows"]) == len(_ROWS)
        print(f"[evaluation e2e] metrics: {list(result['summary'])}")


@pytest.mark.asyncio
async def test_e2e_evaluation_full_flow_async() -> None:
    """Async equivalent of the full one-shot flow."""
    async with AsyncNeuroLinker.from_env() as client:
        job = await client.evaluation.oneshot.jobs.create(dataset=("e2e.jsonl", _jsonl()))
        eval_uid = job.get("eval_uid")
        assert isinstance(eval_uid, str) and eval_uid

        final = await client.evaluation.oneshot.jobs.wait(eval_uid)
        assert final.get("status") == "completed", f"job not completed: {final}"

        result = await client.evaluation.oneshot.results(eval_uid)
        assert result.get("rows") and result.get("summary")
        assert len(result["rows"]) == len(_ROWS)
