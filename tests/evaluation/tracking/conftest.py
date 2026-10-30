from __future__ import annotations

import pytest

from neurolinker_sdk.evaluation.tracking import _tracing


@pytest.fixture(autouse=True)
def _no_sdk_provider():
    """Every test starts and ends as if instrument() never ran."""
    _tracing.swap_provider(None)
    yield
    _tracing.swap_provider(None)


@pytest.fixture()
def exporter():
    """NeuroLinker spans recorded in memory for the test."""
    pytest.importorskip("opentelemetry.sdk")
    from neurolinker_sdk.evaluation.tracking import capture_spans

    with capture_spans() as spans:
        yield spans
