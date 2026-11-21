"""Deterministic, dependency-free text embeddings with an optional upgrade.

The default `HashingEmbedder` needs no model, no network and no API key, so the
project runs on a fresh clone. It captures *lexical* similarity (shared tokens).
For true *semantic* similarity, install `sentence-transformers` and swap in your
own embedder behind the same `.embed(text) -> list[float]` interface — the rest
of the app does not care which one it gets.
"""
from __future__ import annotations

import hashlib
import math
import re
from typing import List

_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def tokenize(text: str) -> List[str]:
    """Split text into lowercase identifier-like tokens."""
    return [t.lower() for t in _TOKEN.findall(text)]


def _l2_normalize(vec: List[float]) -> List[float]:
    """Scale a vector to unit length so cosine similarity is well-behaved."""
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


class HashingEmbedder:
    """Map text to a fixed-size, L2-normalized vector via feature hashing.

    Each token is hashed to one of `dim` buckets with a signed contribution,
    the classic hashing-trick bag-of-words. Fully deterministic across runs.
    """

    def __init__(self, dim: int = 128) -> None:
        self.dim = dim

    def embed(self, text: str) -> List[float]:
        vec = [0.0] * self.dim
        for token in tokenize(text):
            digest = hashlib.md5(token.encode("utf-8")).digest()
            bucket = int.from_bytes(digest[:4], "big")
            sign = 1.0 if (bucket >> 31) & 1 else -1.0
            vec[bucket % self.dim] += sign
        return _l2_normalize(vec)
