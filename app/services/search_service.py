"""Semantic search service: search document chunks via vector similarity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from app.services import embedding_service, vector_service
from app.utils.config import RAG_MIN_SIMILARITY


@dataclass
class SearchHit:
    """A single search result hit."""

    document_id: int
    filename: str
    chunk_index: int
    snippet: str
    similarity: float


def search(
    user_id: int,
    query: str,
    top_k: int = 8,
    min_similarity: Optional[float] = None,
    document_ids: Optional[List[int]] = None,
) -> List[SearchHit]:
    """Semantic search over document chunks, optionally scoped to document_ids.

    Args:
        user_id: The user whose documents to search.
        query: The search query text.
        top_k: Maximum number of hits to return (clamped to 1-20).
        min_similarity: Minimum similarity threshold (0-1). Defaults to
            RAG_MIN_SIMILARITY; never allowed below 0.15.
        document_ids: Optional list of document IDs to scope search to.

    Returns:
        List of SearchHit objects sorted by similarity descending.

    Raises:
        ValueError: If query is empty or whitespace-only.
    """
    if not query or not query.strip():
        raise ValueError("Search query cannot be empty")

    query = query.strip()

    # Clamp top_k to valid range
    top_k = max(1, min(top_k, 20))

    # Resolve minimum similarity threshold
    if min_similarity is None:
        min_similarity = RAG_MIN_SIMILARITY
    if min_similarity < 0.15:
        min_similarity = 0.15

    # Embed the query using the same embedding service as RAG
    query_vec = embedding_service.embed_query(query)

    # Query the vector service (filtered by user_id and optionally document_ids)
    vs = vector_service.get_vector_service()
    results = vs.query(user_id, query_vec, top_k=top_k, document_ids=document_ids)

    # Filter by minimum similarity and build hits
    hits: List[SearchHit] = []
    for r in results:
        if r["similarity"] < min_similarity:
            continue
        meta = r["metadata"]
        text = r["text"]
        snippet = text[:400]
        if len(text) > 400:
            snippet += "..."
        hits.append(
            SearchHit(
                document_id=meta["document_id"],
                filename=meta["filename"],
                chunk_index=meta["chunk_index"],
                snippet=snippet,
                similarity=r["similarity"],
            )
        )

    # Sort by similarity descending
    hits.sort(key=lambda h: h.similarity, reverse=True)
    return hits