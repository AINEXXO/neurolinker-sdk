from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from neurolinker_sdk.chunking import (
    ByTitleConfig,
    ChunkingConfig,
    FixedSizeConfig,
    MarkdownHeaderConfig,
    RecursiveConfig,
    SentenceConfig,
    TokenizerConfig,
)

_adapter: TypeAdapter = TypeAdapter(ChunkingConfig)


# ---------------------------------------------------------------------------
# Happy-path instantiation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cls,method",
    [
        (RecursiveConfig, "recursive"),
        (FixedSizeConfig, "fixed_size"),
        (SentenceConfig, "sentence"),
        (MarkdownHeaderConfig, "markdown_header"),
        (ByTitleConfig, "by_title"),
    ],
)
def test_config_instantiable_with_defaults(cls, method) -> None:
    cfg = cls()
    assert cfg.method == method
    assert cfg.chunk_size is None
    assert cfg.tokenizer is None


def test_recursive_accepts_all_fields() -> None:
    cfg = RecursiveConfig(
        chunk_size=256,
        chunk_overlap=32,
        tokenizer=TokenizerConfig(provider="huggingface", name="BAAI/bge-m3"),
        parse_figures=False,
        parse_tables=True,
        parse_headers=False,
        parse_footers=True,
        metadata_request_uid="550e8400-e29b-41d4-a716-446655440030",
    )
    assert cfg.chunk_size == 256
    assert cfg.chunk_overlap == 32
    assert cfg.tokenizer.name == "BAAI/bge-m3"
    assert cfg.parse_figures is False
    assert cfg.metadata_request_uid == "550e8400-e29b-41d4-a716-446655440030"


def test_tokenizer_accepts_tiktoken_encodings() -> None:
    for encoding in ("cl100k_base", "o200k_base"):
        assert TokenizerConfig(provider="tiktoken", name=encoding).name == encoding


def test_tokenizer_defaults_to_huggingface() -> None:
    assert TokenizerConfig(name="intfloat/e5-large-v2").provider == "huggingface"


# ---------------------------------------------------------------------------
# Discriminated union routing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "payload,cls",
    [
        ({"method": "recursive", "chunk_size": 512}, RecursiveConfig),
        ({"method": "fixed_size", "chunk_size": 400, "chunk_overlap": 40}, FixedSizeConfig),
        ({"method": "sentence", "chunk_overlap": 16}, SentenceConfig),
        ({"method": "markdown_header", "heading_level": 3}, MarkdownHeaderConfig),
        ({"method": "by_title", "min_chunk_size": 100}, ByTitleConfig),
    ],
)
def test_adapter_routes_to_method(payload, cls) -> None:
    assert isinstance(_adapter.validate_python(payload), cls)


def test_adapter_parses_tokenizer_dict() -> None:
    cfg = _adapter.validate_python(
        {"method": "recursive", "tokenizer": {"provider": "tiktoken", "name": "cl100k_base"}}
    )
    assert isinstance(cfg.tokenizer, TokenizerConfig)
    assert cfg.tokenizer.provider == "tiktoken"


def test_adapter_rejects_unknown_method() -> None:
    with pytest.raises(ValidationError):
        _adapter.validate_python({"method": "quantum_chunking"})


@pytest.mark.parametrize("method", ["section_greedy", "md_header_level", "block_window"])
def test_adapter_rejects_removed_methods(method) -> None:
    with pytest.raises(ValidationError):
        _adapter.validate_python({"method": method})


def test_adapter_rejects_missing_method() -> None:
    with pytest.raises(ValidationError):
        _adapter.validate_python({"chunk_size": 512})


# ---------------------------------------------------------------------------
# Per-field validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("size", [15, 8193, 0, -5])
def test_chunk_size_out_of_range_rejected(size) -> None:
    for cls in (RecursiveConfig, MarkdownHeaderConfig, ByTitleConfig):
        with pytest.raises(ValidationError):
            cls(chunk_size=size)


def test_chunk_size_bounds_accepted() -> None:
    assert FixedSizeConfig(chunk_size=16, chunk_overlap=0).chunk_size == 16
    assert FixedSizeConfig(chunk_size=8192).chunk_size == 8192


def test_overlap_must_be_less_than_chunk_size() -> None:
    with pytest.raises(ValidationError):
        RecursiveConfig(chunk_size=100, chunk_overlap=100)
    with pytest.raises(ValidationError):
        SentenceConfig(chunk_size=100, chunk_overlap=200)


def test_overlap_alone_checked_against_default_chunk_size() -> None:
    # The server fills an omitted chunk_size with its default (512).
    with pytest.raises(ValidationError):
        FixedSizeConfig(chunk_overlap=512)
    assert FixedSizeConfig(chunk_overlap=511).chunk_overlap == 511


def test_negative_overlap_rejected() -> None:
    with pytest.raises(ValidationError):
        RecursiveConfig(chunk_overlap=-1)


def test_min_chunk_size_must_be_less_than_chunk_size() -> None:
    with pytest.raises(ValidationError):
        ByTitleConfig(chunk_size=200, min_chunk_size=200)
    assert ByTitleConfig(chunk_size=200, min_chunk_size=199).min_chunk_size == 199


def test_heading_level_out_of_range_rejected() -> None:
    with pytest.raises(ValidationError):
        MarkdownHeaderConfig(heading_level=0)
    with pytest.raises(ValidationError):
        MarkdownHeaderConfig(heading_level=7)


def test_tokenizer_rejects_unknown_tiktoken_encoding() -> None:
    with pytest.raises(ValidationError):
        TokenizerConfig(provider="tiktoken", name="gpt2")


@pytest.mark.parametrize("name", ["", "has space/model", "org/model/extra", "/model"])
def test_tokenizer_rejects_invalid_repository_id(name) -> None:
    with pytest.raises(ValidationError):
        TokenizerConfig(provider="huggingface", name=name)


def test_tokenizer_rejects_unknown_provider() -> None:
    with pytest.raises(ValidationError):
        TokenizerConfig(provider="cohere", name="embed-v3")  # type: ignore[arg-type]


def test_tokenizer_requires_name() -> None:
    with pytest.raises(ValidationError):
        TokenizerConfig()  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# extra='forbid' behavior
# ---------------------------------------------------------------------------


def test_recursive_forbids_unknown_field() -> None:
    with pytest.raises(ValidationError):
        RecursiveConfig(unknown_param=True)  # type: ignore[call-arg]


@pytest.mark.parametrize(
    "cls,field",
    [
        (MarkdownHeaderConfig, "chunk_overlap"),
        (ByTitleConfig, "heading_level"),
        (RecursiveConfig, "min_chunk_size"),
        (FixedSizeConfig, "heading_level"),
    ],
)
def test_forbids_field_from_other_method(cls, field) -> None:
    with pytest.raises(ValidationError):
        cls(**{field: 2})


@pytest.mark.parametrize("field", ["model_name", "t_min", "t_max", "overlap_blocks"])
def test_removed_fields_rejected(field) -> None:
    with pytest.raises(ValidationError):
        RecursiveConfig(**{field: 1})


# ---------------------------------------------------------------------------
# model_dump: exclude_none semantics
# ---------------------------------------------------------------------------


def test_model_dump_excludes_none_fields() -> None:
    cfg = RecursiveConfig(chunk_size=512)
    assert cfg.model_dump(exclude_none=True) == {"method": "recursive", "chunk_size": 512}


def test_model_dump_nests_tokenizer() -> None:
    cfg = SentenceConfig(tokenizer=TokenizerConfig(provider="tiktoken", name="o200k_base"))
    assert cfg.model_dump(exclude_none=True) == {
        "method": "sentence",
        "tokenizer": {"provider": "tiktoken", "name": "o200k_base"},
    }
