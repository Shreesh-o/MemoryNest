"""Full RAG pipeline: query → embed → retrieve → threshold → LLM answer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from app.services import embedding_service, llm_service, vector_service
from app.utils.config import RAG_MIN_SIMILARITY, RAG_TOP_K


@dataclass
class RAGResult:
    answer: str
    sources: List[dict]
    below_threshold: bool


_SYSTEM_PROMPT = (
    "You are a helpful assistant that answers questions ONLY using the provided context. "
    "If the answer is not in the context, say: "
    "\"I couldn't find this information in your stored documents.\" "
    "Do not make up information. Cite sources by their document name and chunk index."
)


def _format_context(results: List[dict]) -> str:
    parts = []
    for i, r in enumerate(results):
        meta = r["metadata"]
        parts.append(
            f"[Source {i+1}] Document: {meta['filename']}, "
            f"Chunk: {meta['chunk_index']}, "
            f"Similarity: {r['similarity']:.3f}\n"
            f"Content: {r['text']}"
        )
    return "\n\n".join(parts)


def _build_prompt(question: str, context: str) -> str:
    return (
        f"Context:\n{context}\n\n"
        f"Question: {question}\n\n"
        f"Answer based only on the context above. "
        f"Include citations like [Source 1], [Source 2] in your answer."
    )


def rag_answer(
    user_id: int,
    question: str,
    top_k: int = RAG_TOP_K,
    min_similarity: float = RAG_MIN_SIMILARITY,
) -> RAGResult:
    """Run the full RAG pipeline for a user's question."""
    # 1. Embed query
    query_vec = embedding_service.embed_query(question)

    # 2. Retrieve
    vs = vector_service.get_vector_service()
    results = vs.query(user_id, query_vec, top_k=top_k)

    # 3. Check threshold
    if not results or results[0]["similarity"] < min_similarity:
        return RAGResult(
            answer="I couldn't find this information in your stored documents.",
            sources=[],
            below_threshold=True,
        )

    # 4. Build prompt and call LLM
    context = _format_context(results)
    prompt = _build_prompt(question, context)
    answer = llm_service.generate(prompt, system=_SYSTEM_PROMPT)

    # 5. Format sources for UI
    sources = [
        {
            "document": r["metadata"]["filename"],
            "chunk_index": r["metadata"]["chunk_index"],
            "similarity": round(r["similarity"], 3),
            "document_id": r["metadata"]["document_id"],
        }
        for r in results
    ]

    return RAGResult(answer=answer, sources=sources, below_threshold=False)