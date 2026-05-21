from __future__ import annotations

import pytest
from pydantic import ValidationError

from neurolinker_sdk.embedding import Content, EmbeddingVector


def test_embedding_vector_rejects_reserved_item_prefix() -> None:
    with pytest.raises(ValidationError):
        EmbeddingVector(
            vector_type="dense",
            field_name="item_dense",
            model_name="ainexxo-bge-m3",
        )


def test_embedding_vector_rejects_reserved_chunk_prefix() -> None:
    with pytest.raises(ValidationError):
        EmbeddingVector(
            vector_type="dense",
            field_name="chunk_anything",
            model_name="ainexxo-bge-m3",
        )


def test_embedding_vector_accepts_internal_model_name() -> None:
    dense = EmbeddingVector(
        vector_type="dense",
        field_name="text_dense",
        model_name="ainexxo-bge-m3",
    )
    assert dense.field_name == "text_dense"


def test_embedding_vector_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        EmbeddingVector.model_validate(
            {
                "vector_type": "dense",
                "field_name": "text_dense",
                "model_name": "voyage/voyage-3.5",
                "api_key": "pa-test",
                "input_type": "document",
            }
        )


def test_content_rejects_unsupported_tables_alias() -> None:
    with pytest.raises(ValidationError):
        Content(
            content_type="tables",
            inputs=["data", "description"],
            vectors=[
                EmbeddingVector(
                    vector_type="dense",
                    field_name="table_dense",
                    model_name="ainexxo-bge-m3",
                ),
            ],
        )


def test_content_rejects_invalid_inputs_for_content_type() -> None:
    with pytest.raises(ValidationError):
        Content(
            content_type="text",
            inputs=["image_base64"],
            vectors=[
                EmbeddingVector(
                    vector_type="dense",
                    field_name="text_dense",
                    model_name="ainexxo-bge-m3",
                ),
            ],
        )


def test_content_builds_with_single_vector() -> None:
    content = Content(
        content_type="text",
        inputs=["content"],
        vectors=[
            EmbeddingVector(
                vector_type="dense",
                field_name="text_dense",
                model_name="ainexxo-bge-m3",
            ),
        ],
    )
    assert content.content_type == "text"


def test_content_rejects_empty_vectors_list() -> None:
    with pytest.raises(ValidationError):
        Content(
            content_type="text",
            inputs=["content"],
            vectors=[],
        )


def test_content_builds_with_multiple_vectors() -> None:
    content = Content(
        content_type="image",
        inputs=["image_base64", "description"],
        vectors=[
            EmbeddingVector(
                vector_type="dense",
                field_name="image_dense",
                model_name="jina_ai/jina-embeddings-v4",
                api_key="jina",
            ),
            EmbeddingVector(
                vector_type="dense",
                field_name="image_dense_2",
                model_name="jina_ai/jina-embeddings-v4",
                api_key="jina",
            ),
        ],
    )
    assert len(content.vectors) == 2
