from __future__ import annotations

from typing import List, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_RESERVED_VECTOR_PREFIXES = ("item_", "chunk_")
_ALLOWED_INPUTS_BY_CONTENT_TYPE = {
    "text": {"content", "header_path"},
    "image": {"description", "extracted_text", "image_base64", "legend", "header_path"},
    "table": {"content", "description", "data", "legend", "header_path"},
}


class EmbeddingVector(BaseModel):
    """A dense or sparse vector to compute for an embedding content block."""

    model_config = ConfigDict(extra="forbid")

    vector_type: Literal["dense", "sparse"]
    field_name: str
    model_name: str
    api_key: str | None = None

    @field_validator("field_name")
    @classmethod
    def _field_name_not_reserved(cls, v: str) -> str:
        for reserved in _RESERVED_VECTOR_PREFIXES:
            if v.startswith(reserved):
                raise ValueError(
                    f"field_name cannot start with '{reserved}' — reserved namespace for internal fields. Got: '{v}'"
                )
        return v


class Content(BaseModel):
    """An embedding content block: a modality plus the vectors to compute for it."""

    model_config = ConfigDict(extra="forbid")

    content_type: Literal["text", "image", "table"]
    inputs: List[str] = Field(default_factory=list)
    vectors: List[EmbeddingVector] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_inputs_for_content_type(self) -> Self:
        allowed = _ALLOWED_INPUTS_BY_CONTENT_TYPE[self.content_type]
        invalid = sorted(set(self.inputs) - allowed)
        if invalid:
            invalid_list = ", ".join(invalid)
            allowed_list = ", ".join(sorted(allowed))
            raise ValueError(
                f"Invalid inputs for content_type '{self.content_type}': {invalid_list}. Allowed inputs: {allowed_list}"
            )
        return self


