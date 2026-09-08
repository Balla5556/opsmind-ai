"""Replaceable embedding providers for runbook retrieval."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, Protocol

import numpy as np


class EmbeddingProvider(Protocol):
    name: str

    def embed(self, texts: list[str]) -> np.ndarray: ...


class SentenceTransformerEmbeddings:
    """Production retrieval provider. The model is loaded only when it is used."""

    name = "sentence-transformers/all-MiniLM-L6-v2"

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", cache_directory: Path | None = None):
        self.model_name = model_name
        self.cache_directory = cache_directory or Path(os.getenv("OPSMIND_MODEL_CACHE", "data/model-cache"))
        self._model = None

    def embed(self, texts: list[str]) -> np.ndarray:
        if self._model is None:
            self.cache_directory.mkdir(parents=True, exist_ok=True)
            # Keep all model activity inside the configured cache. This also avoids
            # the optional Xet client's user-home log/cache writes in containers.
            os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name, cache_folder=str(self.cache_directory))
        vectors = self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return np.asarray(vectors, dtype=np.float32)


class TokenHashEmbeddings:
    """Dependency-free deterministic fallback for offline demos and tests.

    This is intentionally not presented as a semantic model. Deployments should use
    ``SentenceTransformerEmbeddings`` or another approved embedding provider.
    """

    name = "deterministic-token-hash"

    def __init__(self, dimensions: int = 256):
        self.dimensions = dimensions

    def embed(self, texts: list[str]) -> np.ndarray:
        vectors = np.zeros((len(texts), self.dimensions), dtype=np.float32)
        for row, text in enumerate(texts):
            for token in text.lower().replace("_", " ").split():
                index = sum(token.encode("utf-8")) % self.dimensions
                vectors[row, index] += 1.0
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        return vectors / np.maximum(norms, 1e-12)


def configured_embeddings(provider: Literal["semantic", "offline"] | None = None) -> EmbeddingProvider:
    """Return the explicitly configured retrieval provider.

    Semantic embeddings are the runtime default. Offline token hashing is available
    only for disconnected local demos and deterministic tests.
    """
    selected = provider or os.getenv("OPSMIND_EMBEDDING_PROVIDER", "semantic")
    if selected == "semantic":
        return SentenceTransformerEmbeddings()
    if selected == "offline":
        return TokenHashEmbeddings()
    raise ValueError("OPSMIND_EMBEDDING_PROVIDER must be 'semantic' or 'offline'")
