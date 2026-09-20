"""Summary service: map-reduce summarization for long documents."""

from __future__ import annotations

from app.services import llm_service, chunking_service

_MAP_PROMPT = (
    "Summarize the following text concisely, preserving key facts, dates, and numbers. "
    "Keep it to 3-5 sentences.\n\nText:\n{text}"
)

_REDUCE_PROMPT = (
    "Combine the following partial summaries into a single coherent summary. "
    "Preserve all key facts, dates, and numbers. Keep it to 5-7 sentences.\n\nPartial summaries:\n{summaries}"
)


def _map_chunk(text: str) -> str:
    prompt = _MAP_PROMPT.format(text=text)
    return llm_service.generate(prompt, system="You are a precise summarizer.")


def _reduce_summaries(summaries: list[str]) -> str:
    if len(summaries) == 1:
        return summaries[0]
    prompt = _REDUCE_PROMPT.format(summaries="\n\n---\n\n".join(summaries))
    return llm_service.generate(prompt, system="You are a precise summarizer.")


def summarize_document(full_text: str, max_chunk_tokens: int = 1200) -> str:
    """Map-reduce summarization for long documents."""
    if not full_text.strip():
        return ""
    chunks = chunking_service.chunk_text(full_text, max_tokens=max_chunk_tokens, overlap_tokens=100)
    if len(chunks) == 1:
        return _map_chunk(chunks[0].text)
    # Map
    partial = [_map_chunk(c.text) for c in chunks]
    # Reduce
    return _reduce_summaries(partial)