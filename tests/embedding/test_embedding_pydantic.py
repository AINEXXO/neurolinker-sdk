from __future__ import annotations

import pytest
from pydantic import ValidationError

from neurolinker_sdk.embedding import (
    EmbeddingModalities,
    ImageModality,
    ModalityVectors,
    ModelRef,
    TableModality,
    TextModality,
    VectorConfig,
)


def _vc(name: str = "text_dense_bge", endpoint: str = "http://svc/compute") -> VectorConfig:
    return VectorConfig(
        vector_name=name,
        model=ModelRef(endpoint=endpoint, model_name="bge-m3"),
        inputs=["content"],
    )


# ---------------------------------------------------------------------------
# ModelRef
# ---------------------------------------------------------------------------


def test_model_ref_requires_http_or_https_scheme() -> None:
    with pytest.raises(ValidationError):
        ModelRef(endpoint="svc/compute", model_name="bge-m3")
    with pytest.raises(ValidationError):
        ModelRef(endpoint="ftp://svc", model_name="bge-m3")


def test_model_ref_accepts_http_and_https() -> None:
    ModelRef(endpoint="http://svc/compute", model_name="bge-m3")
    ModelRef(endpoint="https://api.voyageai.com/v1/embed", model_name="voyage-multimodal-3")


def test_model_ref_accepts_extra_provider_fields() -> None:
    # extra='allow' for provider-specific fields like Voyage's 'input_type'
    ref = ModelRef.model_validate({
        "endpoint": "https://api.voyageai.com/v1/embed",
        "model_name": "voyage-3",
        "input_type": "document",
    })
    dumped = ref.model_dump(exclude_none=True)
    assert dumped["input_type"] == "document"


def test_model_ref_secret_id_preserved() -> None:
    ref = ModelRef(
        endpoint="https://api.voyageai.com/v1/embed",
        model_name="voyage-3",
        secret_id="neurolinker__user_42__voyage_key",
    )
    assert ref.secret_id == "neurolinker__user_42__voyage_key"


# ---------------------------------------------------------------------------
# VectorConfig
# ---------------------------------------------------------------------------


def test_vector_config_rejects_reserved_item_prefix() -> None:
    with pytest.raises(ValidationError):
        VectorConfig(
            vector_name="item_dense",
            model=ModelRef(endpoint="http://svc", model_name="m"),
        )


def test_vector_config_rejects_reserved_chunk_prefix() -> None:
    with pytest.raises(ValidationError):
        VectorConfig(
            vector_name="chunk_anything",
            model=ModelRef(endpoint="http://svc", model_name="m"),
        )


def test_vector_config_allows_non_reserved_name() -> None:
    cfg = VectorConfig(
        vector_name="text_dense_bge",
        model=ModelRef(endpoint="http://svc", model_name="m"),
        inputs=["content"],
    )
    assert cfg.vector_name == "text_dense_bge"


def test_vector_config_forbids_unknown_field() -> None:
    with pytest.raises(ValidationError):
        VectorConfig.model_validate({
            "vector_name": "text_dense_bge",
            "model": {"endpoint": "http://svc", "model_name": "m"},
            "bogus_field": True,
        })


# ---------------------------------------------------------------------------
# ModalityVectors — multi-vector support
# ---------------------------------------------------------------------------


def test_modality_vectors_accepts_single_dense() -> None:
    mv = ModalityVectors(dense=_vc())
    assert isinstance(mv.dense, VectorConfig)


def test_modality_vectors_accepts_list_of_dense() -> None:
    mv = ModalityVectors(dense=[_vc("text_dense_a"), _vc("text_dense_b")])
    assert isinstance(mv.dense, list)
    assert len(mv.dense) == 2


def test_modality_vectors_accepts_both_dense_and_sparse() -> None:
    mv = ModalityVectors(dense=_vc("text_dense"), sparse=_vc("text_sparse"))
    assert mv.dense is not None and mv.sparse is not None


def test_modality_vectors_allows_none() -> None:
    mv = ModalityVectors()
    assert mv.dense is None and mv.sparse is None


# ---------------------------------------------------------------------------
# EmbeddingModalities
# ---------------------------------------------------------------------------


def test_modalities_accepts_only_text() -> None:
    m = EmbeddingModalities(text=TextModality(vectors=ModalityVectors(dense=_vc())))
    dumped = m.model_dump(exclude_none=True)
    assert set(dumped.keys()) == {"text"}


def test_modalities_rejects_unknown_modality_key() -> None:
    with pytest.raises(ValidationError):
        EmbeddingModalities.model_validate({
            "audio": {"vectors": {"dense": None}},
        })


def test_modalities_to_payload_drops_none() -> None:
    m = EmbeddingModalities(
        text=TextModality(vectors=ModalityVectors(dense=_vc("text_dense"))),
    )
    payload = m.to_payload()
    # sparse not set → absent
    assert "sparse" not in payload["text"]["vectors"]
    # image/table not set → absent
    assert "image" not in payload and "table" not in payload


def test_modalities_accepts_all_three_modalities() -> None:
    m = EmbeddingModalities(
        text=TextModality(vectors=ModalityVectors(dense=_vc("text_dense"))),
        image=ImageModality(vectors=ModalityVectors(dense=_vc("image_dense"))),
        table=TableModality(vectors=ModalityVectors(dense=_vc("table_dense"))),
    )
    payload = m.to_payload()
    assert set(payload.keys()) == {"text", "image", "table"}


# ---------------------------------------------------------------------------
# model_dump — exclude_none / extra='allow' on ModelRef
# ---------------------------------------------------------------------------


def test_vector_config_dump_excludes_none_api_key() -> None:
    cfg = VectorConfig(
        vector_name="text_dense",
        model=ModelRef(endpoint="http://svc", model_name="m"),
    )
    dumped = cfg.model_dump(exclude_none=True)
    assert "api_key" not in dumped["model"]
    assert "secret_id" not in dumped["model"]
