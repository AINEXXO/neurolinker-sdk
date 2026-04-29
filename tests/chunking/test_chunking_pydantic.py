from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from neurolinker_sdk.chunking import (
    BlockWindowConfig,
    ChunkingConfig,
    MdHeaderLevelConfig,
    SectionGreedyConfig,
)

_adapter: TypeAdapter = TypeAdapter(ChunkingConfig)


# ---------------------------------------------------------------------------
# Happy-path instantiation
# ---------------------------------------------------------------------------


def test_section_greedy_instantiable_with_defaults() -> None:
    cfg = SectionGreedyConfig()
    assert cfg.method == "section_greedy"
    assert cfg.t_min is None and cfg.t_max is None


def test_md_header_level_instantiable_with_defaults() -> None:
    cfg = MdHeaderLevelConfig()
    assert cfg.method == "md_header_level"


def test_block_window_instantiable_with_defaults() -> None:
    cfg = BlockWindowConfig()
    assert cfg.method == "block_window"


def test_section_greedy_accepts_all_fields() -> None:
    cfg = SectionGreedyConfig(
        t_min=50, t_max=500, model_name="Alibaba-NLP/gte-large-en-v1.5",
        parse_figures=True, parse_tables=False, parse_headers=True, parse_footers=False,
    )
    assert cfg.t_min == 50
    assert cfg.t_max == 500
    assert cfg.model_name == "Alibaba-NLP/gte-large-en-v1.5"
    assert cfg.parse_figures is True
    assert cfg.parse_tables is False


# ---------------------------------------------------------------------------
# Discriminated-union routing via TypeAdapter
# ---------------------------------------------------------------------------


def test_adapter_routes_to_section_greedy() -> None:
    cfg = _adapter.validate_python({"method": "section_greedy", "t_max": 512})
    assert isinstance(cfg, SectionGreedyConfig)
    assert cfg.t_max == 512


def test_adapter_routes_to_md_header_level() -> None:
    cfg = _adapter.validate_python({"method": "md_header_level", "chunk_at_level": 3})
    assert isinstance(cfg, MdHeaderLevelConfig)
    assert cfg.chunk_at_level == 3


def test_adapter_routes_to_block_window() -> None:
    cfg = _adapter.validate_python({
        "method": "block_window",
        "t_max": 400,
        "overlap_blocks": 2,
        "overlap_mode": "extra_budget",
    })
    assert isinstance(cfg, BlockWindowConfig)
    assert cfg.overlap_mode == "extra_budget"


def test_adapter_rejects_unknown_method() -> None:
    with pytest.raises(ValidationError):
        _adapter.validate_python({"method": "quantum_chunking"})


def test_adapter_rejects_missing_method() -> None:
    with pytest.raises(ValidationError):
        _adapter.validate_python({"t_max": 512})


# ---------------------------------------------------------------------------
# Per-field validation
# ---------------------------------------------------------------------------


def test_section_greedy_rejects_negative_t_min() -> None:
    with pytest.raises(ValidationError):
        SectionGreedyConfig(t_min=0)


def test_section_greedy_rejects_negative_t_max() -> None:
    with pytest.raises(ValidationError):
        SectionGreedyConfig(t_max=-5)


def test_md_header_level_rejects_out_of_range_level() -> None:
    with pytest.raises(ValidationError):
        MdHeaderLevelConfig(chunk_at_level=0)
    with pytest.raises(ValidationError):
        MdHeaderLevelConfig(chunk_at_level=7)


def test_block_window_rejects_negative_overlap_blocks() -> None:
    with pytest.raises(ValidationError):
        BlockWindowConfig(overlap_blocks=-1)


def test_block_window_rejects_invalid_overlap_mode() -> None:
    with pytest.raises(ValidationError):
        BlockWindowConfig(overlap_mode="overflowing")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# extra='forbid' behavior
# ---------------------------------------------------------------------------


def test_section_greedy_forbids_unknown_field() -> None:
    with pytest.raises(ValidationError):
        SectionGreedyConfig(unknown_param=True)  # type: ignore[call-arg]


def test_md_header_level_forbids_field_from_other_method() -> None:
    # t_min belongs to section_greedy, not md_header_level
    with pytest.raises(ValidationError):
        MdHeaderLevelConfig(t_min=50)  # type: ignore[call-arg]


def test_block_window_forbids_field_from_other_method() -> None:
    # chunk_at_level belongs to md_header_level
    with pytest.raises(ValidationError):
        BlockWindowConfig(chunk_at_level=2)  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# model_dump — exclude_none semantics
# ---------------------------------------------------------------------------


def test_model_dump_excludes_none_fields() -> None:
    cfg = SectionGreedyConfig(t_max=512)
    dumped = cfg.model_dump(exclude_none=True)
    assert dumped == {"method": "section_greedy", "t_max": 512}
    # None fields (t_min, model_name, parse_*) are absent
    assert "t_min" not in dumped
    assert "model_name" not in dumped
