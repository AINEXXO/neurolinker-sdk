from __future__ import annotations

from typing import Annotated, Literal, Optional, Self, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _CommonChunkingOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_name: Optional[str] = None
    parse_figures: Optional[bool] = None
    parse_tables: Optional[bool] = None
    parse_headers: Optional[bool] = None
    parse_footers: Optional[bool] = None


class SectionGreedyConfig(_CommonChunkingOptions):
    """Structure-aware chunking respecting a ``t_min``/``t_max`` token budget."""

    method: Literal["section_greedy"] = "section_greedy"
    t_min: Optional[int] = Field(default=None, ge=1)
    t_max: Optional[int] = Field(default=None, ge=1)

    @model_validator(mode="after")
    def _validate_token_budget(self) -> Self:
        if (
            self.t_min is not None
            and self.t_max is not None
            and self.t_min >= self.t_max
        ):
            raise ValueError(
                f"t_min ({self.t_min}) must be less than t_max ({self.t_max})"
            )
        return self


class MdHeaderLevelConfig(_CommonChunkingOptions):
    """Chunks at Markdown header boundaries up to ``chunk_at_level``."""

    method: Literal["md_header_level"] = "md_header_level"
    chunk_at_level: Optional[int] = Field(default=None, ge=1, le=6)


class BlockWindowConfig(_CommonChunkingOptions):
    """Sliding window over blocks with configurable overlap."""

    method: Literal["block_window"] = "block_window"
    t_max: Optional[int] = Field(default=None, ge=1)
    overlap_blocks: Optional[int] = Field(default=None, ge=0)
    overlap_mode: Optional[Literal["within_budget", "extra_budget"]] = None


ChunkingConfig = Annotated[
    Union[SectionGreedyConfig, MdHeaderLevelConfig, BlockWindowConfig],
    Field(discriminator="method"),
]
