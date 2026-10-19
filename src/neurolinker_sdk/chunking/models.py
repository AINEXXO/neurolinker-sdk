from __future__ import annotations

import re
from typing import Annotated, Literal, Optional, Self, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

TIKTOKEN_ENCODINGS = ("cl100k_base", "o200k_base")
DEFAULT_CHUNK_SIZE = 512
MIN_CHUNK_SIZE = 16
MAX_CHUNK_SIZE = 8192

_HF_REPO_ID = re.compile(r"^[A-Za-z0-9][\w.\-]{0,95}(/[\w.\-]{1,96})?$")


class TokenizerConfig(BaseModel):
    """Tokenizer that measures chunk sizes; match it to the embedding model.

    Attributes:
        provider: ``"huggingface"`` for any Hugging Face Hub tokenizer,
            ``"tiktoken"`` for OpenAI encodings.
        name: Hugging Face repository id (e.g. ``BAAI/bge-m3``) or tiktoken
            encoding (``cl100k_base``, ``o200k_base``).
    """

    model_config = ConfigDict(extra="forbid")

    provider: Literal["huggingface", "tiktoken"] = "huggingface"
    name: str

    @model_validator(mode="after")
    def _validate_name(self) -> Self:
        """Validate the name against the provider.

        Returns:
            The validated config.

        Raises:
            ValueError: If the name is not a valid repository id or encoding.
        """
        if self.provider == "tiktoken":
            if self.name not in TIKTOKEN_ENCODINGS:
                raise ValueError(f"tiktoken encoding must be one of {list(TIKTOKEN_ENCODINGS)}")
        elif not _HF_REPO_ID.match(self.name):
            raise ValueError("Hugging Face tokenizer name must be a repository id like 'org/model'")
        return self


class _CommonChunkingOptions(BaseModel):
    """Options valid for every chunking method. Omitted values use the server defaults."""

    model_config = ConfigDict(extra="forbid")

    tokenizer: Optional[TokenizerConfig] = None
    parse_figures: Optional[bool] = None
    parse_tables: Optional[bool] = None
    parse_headers: Optional[bool] = None
    parse_footers: Optional[bool] = None
    metadata_request_uid: Optional[str] = None

    def _check_below_chunk_size(self, field: str) -> None:
        """Reject a ``field`` value that is not below the effective chunk size.

        The effective chunk size is the given ``chunk_size`` or the server
        default, matching how the server resolves the configuration.

        Args:
            field: Name of the field that must stay below ``chunk_size``.

        Raises:
            ValueError: If the value is set and not less than the chunk size.
        """
        value = getattr(self, field)
        size = getattr(self, "chunk_size", None) or DEFAULT_CHUNK_SIZE
        if value is not None and value >= size:
            raise ValueError(f"{field} ({value}) must be less than chunk_size ({size})")


class _OverlapChunkingOptions(_CommonChunkingOptions):
    """Options shared by the size-driven methods with overlap."""

    chunk_size: Optional[int] = Field(default=None, ge=MIN_CHUNK_SIZE, le=MAX_CHUNK_SIZE)
    chunk_overlap: Optional[int] = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _validate_overlap(self) -> Self:
        """Ensure the overlap is smaller than the chunk size.

        Returns:
            The validated config.

        Raises:
            ValueError: If ``chunk_overlap`` is not less than ``chunk_size``.
        """
        self._check_below_chunk_size("chunk_overlap")
        return self


class RecursiveConfig(_OverlapChunkingOptions):
    """Splits on the largest boundary that fits (paragraph, line, sentence, word)
    and packs the pieces up to ``chunk_size`` tokens, with token overlap.
    General-purpose default."""

    method: Literal["recursive"] = "recursive"


class FixedSizeConfig(_OverlapChunkingOptions):
    """Windows of exactly ``chunk_size`` tokens with token overlap, cut anywhere
    in the text. Figures and tables are kept whole."""

    method: Literal["fixed_size"] = "fixed_size"


class SentenceConfig(_OverlapChunkingOptions):
    """Packs whole sentences up to ``chunk_size`` tokens, with whole-sentence
    overlap. A sentence is only cut when it alone exceeds the chunk size."""

    method: Literal["sentence"] = "sentence"


class MarkdownHeaderConfig(_CommonChunkingOptions):
    """One chunk per section at ``heading_level``; deeper sections stay with
    their parent, oversized sections are split to fit ``chunk_size``."""

    method: Literal["markdown_header"] = "markdown_header"
    heading_level: Optional[int] = Field(default=None, ge=1, le=6)
    chunk_size: Optional[int] = Field(default=None, ge=MIN_CHUNK_SIZE, le=MAX_CHUNK_SIZE)


class ByTitleConfig(_CommonChunkingOptions):
    """A new chunk at every heading; sections are combined while the chunk is
    below ``min_chunk_size`` and the result fits ``chunk_size``."""

    method: Literal["by_title"] = "by_title"
    chunk_size: Optional[int] = Field(default=None, ge=MIN_CHUNK_SIZE, le=MAX_CHUNK_SIZE)
    min_chunk_size: Optional[int] = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _validate_min_chunk_size(self) -> Self:
        """Ensure the minimum chunk size is smaller than the chunk size.

        Returns:
            The validated config.

        Raises:
            ValueError: If ``min_chunk_size`` is not less than ``chunk_size``.
        """
        self._check_below_chunk_size("min_chunk_size")
        return self


ChunkingConfig = Annotated[
    Union[RecursiveConfig, FixedSizeConfig, SentenceConfig, MarkdownHeaderConfig, ByTitleConfig],
    Field(discriminator="method"),
]
