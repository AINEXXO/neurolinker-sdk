from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# Abstract dtypes accepted by the backend collection schema. The concrete
# provider (Milvus/Qdrant/Pinecone) translates these to native types.
DType = Literal[
    "text",
    "int",
    "float",
    "bool",
    "json",
    "dense_vector",
    "sparse_vector",
]

Distance = Literal["cosine", "dot", "euclidean"]


class FieldDef(BaseModel):
    """Public field definition for collection creation.

    Uses abstract dtypes — the provider translates them to native types.
    Provider-specific options go in ``options`` (e.g. Milvus's
    ``enable_analyzer``). Each provider reads only the options it
    understands and ignores the rest.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    dtype: DType
    dim: Optional[int] = Field(default=None, ge=1)
    distance: Distance = "cosine"
    is_primary: bool = False
    options: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def _name_non_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("Field name cannot be empty")
        return v

    @model_validator(mode="after")
    def _dense_vector_requires_dim(self) -> "FieldDef":
        if self.dtype == "dense_vector" and (self.dim is None or self.dim <= 0):
            raise ValueError(
                f"Field '{self.name}': dense_vector requires dim > 0"
            )
        return self


class CollectionSchema(BaseModel):
    """Collection definition passed to ``POST /v1/vector-store/collections``."""

    model_config = ConfigDict(extra="forbid")

    name: str
    fields: List[FieldDef] = Field(min_length=1)
    description: str = ""

    @field_validator("name")
    @classmethod
    def _name_non_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("Collection name cannot be empty")
        return v

    @model_validator(mode="after")
    def _validate_fields(self) -> "CollectionSchema":
        names = [f.name for f in self.fields]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate field names in collection")
        primary_keys = [f for f in self.fields if f.is_primary]
        if len(primary_keys) > 1:
            raise ValueError("Collection can have at most one primary key field")
        return self


class VectorDBConfig(BaseModel):
    """Vector database connection configuration.

    Pass ``secret_id`` to reference the credential by Secret Manager id;
    the actual value is resolved server-side at job execution time.
    """

    model_config = ConfigDict(extra="forbid")

    uri: str
    secret_id: Optional[str] = None
    timeout: int = 300

    @field_validator("uri")
    @classmethod
    def _uri_non_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("uri cannot be empty")
        return v


class FieldMapping(BaseModel):
    """Mapping from a source field in the flat record to a collection field.

    ``source`` naming — three non-overlapping namespaces:

    * ``item_*``       → embedding item fields (``item_id``, ``item_content``, ...)
    * ``chunk_*``      → parent chunk fields (``chunk_id``, ``chunk_source_file``, ...)
    * ``<vector_name>``→ free name chosen in the Embedding request
      (e.g. ``text_dense_bge``). This is the explicit coupling point with
      Embedding.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    source: str

    @field_validator("name", "source")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("must be a non-empty string")
        return v