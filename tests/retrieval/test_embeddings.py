"""Tests for the embedding provider and cosine similarity."""

from __future__ import annotations

import math

import pytest
from app.core.config import Settings
from app.retrieval.embeddings import HashingEmbeddingProvider, get_embedding_provider
from app.retrieval.store import cosine_similarity


def test_embedding_is_deterministic_and_right_dim() -> None:
    p = HashingEmbeddingProvider(dim=64)
    v1 = p.embed(["orders table migration"])[0]
    v2 = p.embed(["orders table migration"])[0]
    assert v1 == v2  # deterministic
    assert len(v1) == 64


def test_embedding_is_l2_normalized() -> None:
    p = HashingEmbeddingProvider(dim=128)
    vec = p.embed(["some non-empty text with tokens"])[0]
    assert math.isclose(math.sqrt(sum(x * x for x in vec)), 1.0, rel_tol=1e-9)


def test_empty_text_is_zero_vector() -> None:
    p = HashingEmbeddingProvider(dim=32)
    assert p.embed([""])[0] == [0.0] * 32


def test_similar_text_scores_higher_than_unrelated() -> None:
    p = HashingEmbeddingProvider(dim=512)
    base = p.embed(["add orders table and order model migration"])[0]
    related = p.embed(["add orders api endpoint returning order model"])[0]
    unrelated = p.embed(["bump uvicorn dependency version"])[0]

    assert cosine_similarity(base, related) > cosine_similarity(base, unrelated)


def test_zero_dim_rejected() -> None:
    with pytest.raises(ValueError):
        HashingEmbeddingProvider(dim=0)


def test_get_embedding_provider_from_settings() -> None:
    settings = Settings(embedding_provider="hash", embed_dim=100)
    provider = get_embedding_provider(settings)
    assert provider.name == "hash"
    assert provider.dim == 100


def test_cosine_similarity_edge_cases() -> None:
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
    assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0  # zero vector
    assert cosine_similarity([1.0], [1.0, 2.0]) == 0.0  # length mismatch
