import pytest
from neurolinker_sdk.config import NeuroLinkerConfig, DEFAULT_BASE_URL
from neurolinker_sdk.errors import NeuroLinkerConfigError


def test_from_env_requires_token(monkeypatch):
    monkeypatch.delenv("NEUROLINKER_TOKEN", raising=False)
    monkeypatch.delenv("NEUROLINKER_BASE_URL", raising=False)

    with pytest.raises(NeuroLinkerConfigError):
        NeuroLinkerConfig.from_env()


def test_from_env_uses_default_base_url_when_missing(monkeypatch):
    monkeypatch.setenv("NEUROLINKER_TOKEN", "nl_dummy")
    monkeypatch.delenv("NEUROLINKER_BASE_URL", raising=False)

    cfg = NeuroLinkerConfig.from_env()
    assert cfg.base_url == DEFAULT_BASE_URL.rstrip("/")
    assert cfg.token == "nl_dummy"


def test_from_env_respects_custom_base_url(monkeypatch):
    monkeypatch.setenv("NEUROLINKER_TOKEN", "nl_dummy")
    monkeypatch.setenv("NEUROLINKER_BASE_URL", "https://example.com/neurolinker/")

    cfg = NeuroLinkerConfig.from_env()
    assert cfg.base_url == "https://example.com/neurolinker"