import pytest
from neurolinker_sdk.config import (
    DEFAULT_BASE_URL,
    DEFAULT_POLL_INTERVAL_S,
    DEFAULT_POLL_MAX_INTERVAL_S,
    DEFAULT_TIMEOUT_S,
    NeuroLinkerConfig,
)
from neurolinker_sdk.errors import NeuroLinkerConfigError


def test_from_env_requires_token(monkeypatch):
    monkeypatch.delenv("NEUROLINKER_API_KEY", raising=False)
    monkeypatch.delenv("NEUROLINKER_BASE_URL", raising=False)

    with pytest.raises(NeuroLinkerConfigError):
        NeuroLinkerConfig.from_env()


def test_from_env_uses_default_base_url_when_missing(monkeypatch):
    monkeypatch.setenv("NEUROLINKER_API_KEY", "nl_dummy")
    monkeypatch.delenv("NEUROLINKER_BASE_URL", raising=False)
    monkeypatch.delenv("NEUROLINKER_E2E_TIMEOUT_S", raising=False)
    monkeypatch.delenv("NEUROLINKER_E2E_POLL_INTERVAL_S", raising=False)
    monkeypatch.delenv("NEUROLINKER_E2E_POLL_MAX_INTERVAL_S", raising=False)

    cfg = NeuroLinkerConfig.from_env()
    assert cfg.base_url == DEFAULT_BASE_URL.rstrip("/")
    assert cfg.token == "nl_dummy"
    assert cfg.timeout_s == DEFAULT_TIMEOUT_S
    assert cfg.poll_interval_s == DEFAULT_POLL_INTERVAL_S
    assert cfg.poll_max_interval_s == DEFAULT_POLL_MAX_INTERVAL_S


def test_from_env_respects_custom_base_url(monkeypatch):
    monkeypatch.setenv("NEUROLINKER_API_KEY", "nl_dummy")
    monkeypatch.setenv("NEUROLINKER_BASE_URL", "https://example.com/neurolinker/")
    monkeypatch.setenv("NEUROLINKER_E2E_TIMEOUT_S", "123")
    monkeypatch.setenv("NEUROLINKER_E2E_POLL_INTERVAL_S", "1.5")
    monkeypatch.setenv("NEUROLINKER_E2E_POLL_MAX_INTERVAL_S", "7.0")

    cfg = NeuroLinkerConfig.from_env()
    assert cfg.base_url == "https://example.com/neurolinker"
    assert cfg.timeout_s == 123.0
    assert cfg.poll_interval_s == 1.5
    assert cfg.poll_max_interval_s == 7.0
