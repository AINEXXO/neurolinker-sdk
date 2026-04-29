from __future__ import annotations

import pytest
from pydantic import ValidationError

from neurolinker_sdk.vector_store import (
    CollectionSchema,
    FieldDef,
    FieldMapping,
    VectorDBConfig,
)

# ---------------------------------------------------------------------------
# FieldDef — dtype enum + dense_vector dim requirement
# ---------------------------------------------------------------------------


def test_field_def_accepts_all_abstract_dtypes() -> None:
    FieldDef(name="a", dtype="text")
    FieldDef(name="b", dtype="int")
    FieldDef(name="c", dtype="float")
    FieldDef(name="d", dtype="bool")
    FieldDef(name="e", dtype="json")
    FieldDef(name="v", dtype="dense_vector", dim=1024)
    FieldDef(name="s", dtype="sparse_vector")


def test_field_def_rejects_unknown_dtype() -> None:
    with pytest.raises(ValidationError):
        FieldDef(name="x", dtype="VARCHAR")  # type: ignore[arg-type]


def test_field_def_rejects_empty_name() -> None:
    with pytest.raises(ValidationError):
        FieldDef(name="", dtype="text")


def test_dense_vector_requires_dim() -> None:
    with pytest.raises(ValidationError):
        FieldDef(name="v", dtype="dense_vector")


def test_dense_vector_rejects_zero_dim() -> None:
    with pytest.raises(ValidationError):
        FieldDef(name="v", dtype="dense_vector", dim=0)


def test_sparse_vector_does_not_require_dim() -> None:
    cfg = FieldDef(name="s", dtype="sparse_vector")
    assert cfg.dim is None


def test_field_def_forbids_unknown_field() -> None:
    with pytest.raises(ValidationError):
        FieldDef.model_validate({
            "name": "x",
            "dtype": "text",
            "bogus": True,
        })


def test_field_def_default_distance_is_cosine() -> None:
    cfg = FieldDef(name="v", dtype="dense_vector", dim=128)
    assert cfg.distance == "cosine"


def test_field_def_accepts_options_dict() -> None:
    cfg = FieldDef(
        name="content",
        dtype="text",
        options={"enable_analyzer": True, "enable_match": True},
    )
    assert cfg.options == {"enable_analyzer": True, "enable_match": True}


# ---------------------------------------------------------------------------
# CollectionSchema
# ---------------------------------------------------------------------------


def test_collection_schema_requires_at_least_one_field() -> None:
    with pytest.raises(ValidationError):
        CollectionSchema(name="c", fields=[])


def test_collection_schema_rejects_empty_name() -> None:
    with pytest.raises(ValidationError):
        CollectionSchema(name="", fields=[FieldDef(name="a", dtype="text")])


def test_collection_schema_rejects_duplicate_field_names() -> None:
    with pytest.raises(ValidationError):
        CollectionSchema(
            name="c",
            fields=[
                FieldDef(name="dup", dtype="text"),
                FieldDef(name="dup", dtype="int"),
            ],
        )


def test_collection_schema_rejects_multiple_primary_keys() -> None:
    with pytest.raises(ValidationError):
        CollectionSchema(
            name="c",
            fields=[
                FieldDef(name="a", dtype="text", is_primary=True),
                FieldDef(name="b", dtype="text", is_primary=True),
            ],
        )


def test_collection_schema_accepts_single_primary_key() -> None:
    cs = CollectionSchema(
        name="c",
        fields=[
            FieldDef(name="id", dtype="text", is_primary=True),
            FieldDef(name="content", dtype="text"),
        ],
    )
    assert len(cs.fields) == 2


# ---------------------------------------------------------------------------
# VectorDBConfig
# ---------------------------------------------------------------------------


def test_vector_db_config_rejects_empty_uri() -> None:
    with pytest.raises(ValidationError):
        VectorDBConfig(uri="")


def test_vector_db_config_secret_id_preserved() -> None:
    cfg = VectorDBConfig(
        uri="https://example.zilliz.com",
        secret_id="neurolinker__user_42__milvus_token",
    )
    assert cfg.secret_id == "neurolinker__user_42__milvus_token"
    assert cfg.api_key is None


def test_vector_db_config_default_timeout() -> None:
    cfg = VectorDBConfig(uri="https://example.zilliz.com")
    assert cfg.timeout == 300


def test_vector_db_config_forbids_unknown_field() -> None:
    with pytest.raises(ValidationError):
        VectorDBConfig.model_validate({
            "uri": "https://example",
            "bogus": True,
        })


# ---------------------------------------------------------------------------
# FieldMapping
# ---------------------------------------------------------------------------


def test_field_mapping_requires_both_name_and_source() -> None:
    fm = FieldMapping(name="chunk_id", source="item_id")
    assert fm.name == "chunk_id" and fm.source == "item_id"


def test_field_mapping_rejects_empty_source() -> None:
    with pytest.raises(ValidationError):
        FieldMapping(name="x", source="")


def test_field_mapping_rejects_empty_name() -> None:
    with pytest.raises(ValidationError):
        FieldMapping(name="", source="item_id")


def test_field_mapping_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        FieldMapping.model_validate({
            "name": "x",
            "source": "item_id",
            "dtype": "VARCHAR",  # legacy field, not part of the minimal API
        })


# ---------------------------------------------------------------------------
# model_dump — excluded fields
# ---------------------------------------------------------------------------


def test_vector_db_config_dump_excludes_none_api_key() -> None:
    cfg = VectorDBConfig(uri="https://example", secret_id="s")
    dumped = cfg.model_dump(exclude_none=True)
    assert "api_key" not in dumped
    assert dumped["secret_id"] == "s"
