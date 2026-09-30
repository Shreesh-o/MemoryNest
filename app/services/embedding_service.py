"""Embedding service using sentence-transformers (CPU)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

from app.utils.config import EMBEDDING_MODEL

_model = None
_model_loaded = False


def _is_model_cached(model_name: str) -> bool:
    """Check if the model is already in the local HF cache."""
    cache_dir = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface"))
    # sentence-transformers stores models in hub/models--<org>--<model_name>
    model_dir = cache_dir / "hub" / f"models--{model_name.replace('/', '--')}"
    return model_dir.exists()


def _get_model():
    global _model, _model_loaded
    if _model is None:
        # Set HF_HUB_OFFLINE=1 only if model is already cached
        if _is_model_cached(EMBEDDING_MODEL):
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
        else:
            os.environ.setdefault("HF_HUB_OFFLINE", "0")
            import logging
            logging.getLogger(__name__).info(
                "Embedding model '%s' not found in cache; will download on first use.",
                EMBEDDING_MODEL,
            )
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(EMBEDDING_MODEL)
        _model_loaded = True
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