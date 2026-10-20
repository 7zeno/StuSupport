"""Text embeddings for RAG.

Uses sentence-transformers (all-MiniLM-L6-v2, 384-dim) when installed. If it is
not installed, falls back to a deterministic hashed bag-of-words embedder with
the same dimension so the schema doesn't change. The fallback is only for
offline development; retrieval quality is noticeably better with the real model.

Re-run ingestion after switching embedders (vectors from the two are not comparable).
"""
import hashlib
import re
from functools import lru_cache

import numpy as np

from ..config import get_settings

settings = get_settings()
_TOKEN = re.compile(r"[a-z0-9]+")
_STOP = set(
    "a an and are as at be by for from has have i if in is it its my of on or so that the this to was were will with "
    "you your me we our can do does how what when where which who why".split()
)


class _HashingEmbedder:
    name = "hashing-bow-384"

    def __init__(self, dim: int):
        self.dim = dim

    def _vec(self, text: str) -> np.ndarray:
        toks = [t for t in _TOKEN.findall(text.lower()) if t not in _STOP]
        grams = toks + [f"{a}_{b}" for a, b in zip(toks, toks[1:])]
        v = np.zeros(self.dim, dtype=np.float32)
        for g in grams:
            h = int(hashlib.md5(g.encode()).hexdigest(), 16)
            v[h % self.dim] += 1.0 if (h >> 64) & 1 else -1.0
        n = np.linalg.norm(v)
        return v / n if n else v

    def encode(self, texts: list[str]) -> np.ndarray:
        return np.vstack([self._vec(t) for t in texts])


class _STEmbedder:
    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name)
        self.name = model_name

    def encode(self, texts: list[str]) -> np.ndarray:
        return np.asarray(self.model.encode(texts, normalize_embeddings=True), dtype=np.float32)


@lru_cache
def get_embedder():
    try:
        return _STEmbedder(settings.embedding_model)
    except ImportError:
        return _HashingEmbedder(settings.embedding_dim)
