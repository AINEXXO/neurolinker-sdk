from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

_RESERVED_VECTOR_PREFIXES = ("item_", "chunk_")

class ModelRef(BaseModel):
    """Embedding model endpoint reference.

    Provider is auto-detected server-side from the endpoint domain (internal,
    ``jina.ai``, ``voyageai.com``, ...). Provider-specific fields (e.g. Voyage's
    ``input_type``) are passed through as-is via ``extra="allow"``.

    For external providers, pass ``secret_id`` to reference the provider's
    credential by Secret Manager id; the actual value is resolved server-side
    at job execution time. Internal models need no credential.
    """

    model_config = ConfigDict(extra="allow")

    endpoint: str
    model_name: str
    secret_id: Optional[str] = None

    @field_validator("endpoint")
    @classmethod
    def _endpoint_must_be_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError(
                "endpoint must be a valid URL starting with http:// or https://"
            )
        return v


class VectorConfig(BaseModel):
    """One vector (dense or sparse) for a modality."""

    model_config = ConfigDict(extra="forbid")

    vector_name: str
    model: ModelRef
    inputs: List[str] = Field(default_factory=list)

    @field_validator("vector_name")
    @classmethod
    def _vector_name_not_reserved(cls, v: str) -> str:
        for reserved in _RESERVED_VECTOR_PREFIXES:
            if v.startswith(reserved):
                raise ValueError(
                    f"vector_name cannot start with '{reserved}' — reserved "
                    f"namespace for internal fields. Got: '{v}'"
                )
        return v


class ModalityVectors(BaseModel):
    """Dense and/or sparse vector configs for a modality.

    Each slot accepts a single ``VectorConfig`` or a list (multiple vectors per
    type — e.g. two dense models in parallel).
    """

    model_config = ConfigDict(extra="forbid")

    dense: Optional[Union[VectorConfig, List[VectorConfig]]] = None
    sparse: Optional[Union[VectorConfig, List[VectorConfig]]] = None


class TextModality(BaseModel):
    model_config = ConfigDict(extra="forbid")
    vectors: ModalityVectors


class ImageModality(BaseModel):
    model_config = ConfigDict(extra="forbid")
    vectors: ModalityVectors


class TableModality(BaseModel):
    model_config = ConfigDict(extra="forbid")
    vectors: ModalityVectors


class EmbeddingModalities(BaseModel):
    """Top-level modality container for an embedding job."""

    model_config = ConfigDict(extra="forbid")

    text: Optional[TextModality] = None
    image: Optional[ImageModality] = None
    table: Optional[TableModality] = None

    def to_payload(self) -> Dict[str, Any]:
        """Serialize to the JSON shape expected by ``POST /v1/embed/jobs``.

        Only populated modalities are included; ``None`` fields are dropped.
        """
        return self.model_dump(exclude_none=True)

