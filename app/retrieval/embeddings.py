"""Embedding provider abstraction.

An embedding provider turns text into a fixed-dimension vector. The default
``HashingEmbeddingProvider`` is offline and deterministic — no network, no key —
so tests and demos produce stable, comparable vectors. It uses signed feature
hashing (a bag-of-words hashed into buckets with +/- signs) and L2-normalizes,
which keeps similar text close in cosine space so retrieval ordering is
meaningful and testable.

A real, provider-backed embedder plugs in behind ``EMBEDDING_PROVIDER`` later;
``get_embedding_provider`` is the single selection point.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol, runtime_checkable

from app.core.config import Settings

_TOKEN_RE = re.compile(r"[a-z0-9]+")


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Structural interface every embedding provider implements."""

    name: str
    model: str
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per input text."""
        ...


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class HashingEmbeddingProvider:
    """Deterministic, offline embedder via signed feature hashing."""

    name = "hash"
    model = "hash-v1"

    def __init__(self, dim: int = 256) -> None:
        if dim <= 0:
            raise ValueError("embedding dim must be positive")
        self.dim = dim

    def _embed_one(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for token in _tokenize(text):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            h = int.from_bytes(digest, "big")
            idx = h % self.dim
            sign = 1.0 if (h >> 1) & 1 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0.0:
            vec = [v / norm for v in vec]
        return vec

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]


def get_embedding_provider(settings: Settings) -> EmbeddingProvider:
    """Select an embedding provider from settings (only ``hash`` for now)."""
    if settings.embedding_provider == "hash":
        return HashingEmbeddingProvider(dim=settings.embed_dim)
    raise ValueError(f"Unknown embedding provider: {settings.embedding_provider!r}")
