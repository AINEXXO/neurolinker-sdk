import os
import time
import uuid

import pytest

from neurolinker_sdk import NeuroLinker, instrument, record_query

TOKEN = os.getenv("NEUROLINKER_API_KEY")

pytestmark = pytest.mark.skipif(
    not TOKEN,
    reason="Set NEUROLINKER_API_KEY to run this E2E test.",
)
# Needs the tracking extra (OpenTelemetry + OpenInference) installed.
pytest.importorskip("opentelemetry")
pytest.importorskip("openinference.semconv")

# How long to wait for the asynchronous backend evaluation (ingest grace window +
# Ragas judge) to produce the scored record.
_EVAL_TIMEOUT_S = 180
_POLL_INTERVAL_S = 5


def test_e2e_tracking_full_flow_sync() -> None:
    """End-to-end manual-tracking flow:
    1) create a track
    2) instrument() + record one query (custom-RAG path, no framework needed)
    3) poll the dashboard until the backend has scored that query
    4) disable the track (cleanup)
    """
    marker = uuid.uuid4().hex
    question = f"What is the capital of France? [{marker}]"

    with NeuroLinker.from_env() as client:
        track = client.evaluation.tracking.tracks.create(name=f"sdk-e2e-{marker[:8]}")
        track_uid = track["track_uid"]
        assert track_uid, f"missing track_uid: {track}"
        print(f"[tracking e2e] track_uid={track_uid}")

        try:
            provider = instrument(track_uid=track_uid, api_key=TOKEN)
            with record_query(user_input=question) as q:
                q.set_contexts(["Paris is the capital and largest city of France."])
                q.set_response("The capital of France is Paris.")
                q.set_llm(model="sdk-e2e", input_tokens=20, output_tokens=8)
            provider.force_flush()  # short-lived: push the spans now

            deadline = time.monotonic() + _EVAL_TIMEOUT_S
            found = None
            while time.monotonic() < deadline:
                rows = client.evaluation.tracking.queries(track_uid, limit=50)["queries"]
                found = next((r for r in rows if r.get("user_input") == question), None)
                if found is not None:
                    break
                time.sleep(_POLL_INTERVAL_S)

            assert found is not None, (
                f"query was not scored within {_EVAL_TIMEOUT_S}s (track={track_uid})"
            )
            print(f"[tracking e2e] scored: metrics={found.get('metrics')}")
            assert "trace_id" in found
        finally:
            client.evaluation.tracking.tracks.set_active(track_uid, active=False)
