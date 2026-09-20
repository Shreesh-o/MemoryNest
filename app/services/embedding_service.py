"""Embedding service using sentence-transformers (CPU)."""

from __future__ import annotations

from typing import List

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        from app.utils.config import EMBEDDING_MODEL
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Embed a list of texts. Returns list of float vectors (normalized)."""
    if not texts:
        return []
    model = _get_model()
    # encode normalizes by default for sentence-transformers with `normalize_embeddings=True`
    # (which is the default for most models including all-MiniLM-L6-v2)
    return model.encode(texts, normalize_embeddings=True, show_progress_bar=False).tolist()


def embed_query(text: str) -> List[float]:
    """Embed a single query text."""
    return embed_texts([text])[0]