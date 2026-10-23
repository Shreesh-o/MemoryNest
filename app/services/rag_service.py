"""Full RAG pipeline: query → embed → retrieve → threshold → LLM answer."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

from app.services import embedding_service, llm_service, vector_service
from app.utils.config import RAG_MIN_SIMILARITY, RAG_TOP_K


@dataclass
class RAGResult:
    answer: str
    sources: List[dict]
    below_threshold: bool
    scope: Optional[dict] = None


_SYSTEM_PROMPT = (
    "You are a helpful assistant that answers questions ONLY using the provided context. "
    "If the answer is not in the context, say: "
    "\"I couldn't find this information in your stored documents.\" "
    "Do not make up information. Answer in your own words. Do not cite sources inline "
    "or include source headers; citations are shown separately."
)

_SCOPED_SYSTEM_PROMPT = (
    "You are a helpful assistant that answers questions ONLY using the provided context. "
    "If the answer is not in the context, say: "
    "\"I couldn't find this information in the selected documents.\" "
    "Do not make up information. Answer in your own words. Do not cite sources inline "
    "or include source headers; citations are shown separately."
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
        f"Answer based only on the context above in your own words."
    )


def _strip_source_headers(text: str) -> str:
    """Strip "[Source n] Document: ..., Chunk: ..., Similarity: ..." header lines.

    The LLM may echo these header lines from the context into its answer.
    Remove them so the answer text contains only natural-language content,
    while the structured sources list (returned separately) remains available
    to the UI.
    """
    pattern = re.compile(
        r"^\[Source \d+\] Document: .*?\n",
        re.MULTILINE,
    )
    return pattern.sub("", text)


def rag_answer(
    user_id: int,
    question: str,
    top_k: int = RAG_TOP_K,
    min_similarity: float = RAG_MIN_SIMILARITY,
    document_ids: Optional[List[int]] = None,
) -> RAGResult:
    """Run the full RAG pipeline for a user's question, optionally filtered by document_ids."""
    scope = (
        {"scope": "selected", "document_ids": list(document_ids)}
        if document_ids is not None
        else {"scope": "all", "document_ids": None}
    )

    # 1. Embed query
    query_vec = embedding_service.embed_query(question)

    # 2. Retrieve
    vs = vector_service.get_vector_service()
    results = vs.query(user_id, query_vec, top_k=top_k, document_ids=document_ids)

    # 3. Check threshold
    if not results or results[0]["similarity"] < min_similarity:
        refusal_msg = (
            "I couldn't find this information in the selected documents."
            if document_ids is not None
            else "I couldn't find this information in your stored documents."
        )
        return RAGResult(
            answer=refusal_msg,
            sources=[],
            below_threshold=True,
            scope=scope,
        )

    # 4. Build prompt and call LLM
    context = _format_context(results)
    prompt = _build_prompt(question, context)
    system_prompt = _SCOPED_SYSTEM_PROMPT if document_ids is not None else _SYSTEM_PROMPT
    answer = llm_service.generate(prompt, system=system_prompt)
    # Strip any "[Source n] Document: ..., Chunk: ..., Similarity: ..." header
    # lines that the model may have echoed from the context into the answer.
    answer = _strip_source_headers(answer)

    # If the model echoed the un-scoped refusal while scoped, adjust it
    if document_ids is not None and "stored documents" in answer:
        answer = answer.replace("stored documents", "selected documents")

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

    return RAGResult(answer=answer, sources=sources, below_threshold=False, scope=scope)