"""Text chunking: sentence-aware, target ~450 tokens with ~50 token overlap.

Token counting uses a character heuristic (~4 chars per token), which is
stable and dependency-free. Good enough for retrieval chunking.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    return max(1, round(len(text) / _CHARS_PER_TOKEN))


@dataclass
class Chunk:
    index: int
    text: str
    token_count: int


_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+|\n+")


def _split_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in _SENTENCE_RE.split(text) if p.strip()]
    return parts


def _hard_split(text: str, max_chars: int) -> list[str]:
    """Split an oversized piece by words so no part exceeds max_chars."""
    words = text.split()
    if not words:
        return []
    pieces: list[str] = []
    current: list[str] = []
    current_len = 0
    for w in words:
        add = len(w) + (1 if current else 0)
        if current and current_len + add > max_chars:
            pieces.append(" ".join(current))
            current, current_len = [w], len(w)
        else:
            current.append(w)
            current_len += add
    if current:
        pieces.append(" ".join(current))
    return pieces


def _overlap_tail(chunk_text: str, overlap_chars: int) -> list[str]:
    """Return the trailing words of a chunk that fit within overlap_chars."""
    tail: list[str] = []
    tail_len = 0
    for word in reversed(chunk_text.split()):
        add = len(word) + (1 if tail_len else 0)
        if tail_len and tail_len + add > overlap_chars:
            break
        tail.append(word)
        tail_len += add
    return list(reversed(tail))


def chunk_text(text: str, max_tokens: int = 450, overlap_tokens: int = 50) -> list[Chunk]:
    """Split text into overlapping chunks.

    Every chunk except the first starts with up to `overlap_tokens` of the
    previous chunk's trailing words, so context is not lost at boundaries.
    Chunk content budget is reduced by the overlap so total size stays
    within `max_tokens`.
    """
    text = (text or "").strip()
    if not text:
        return []
    if estimate_tokens(text) <= max_tokens:
        return [Chunk(0, text, estimate_tokens(text))]

    overlap_chars = max(0, min(overlap_tokens, max_tokens - 1)) * _CHARS_PER_TOKEN
    content_chars = max(1, max_tokens * _CHARS_PER_TOKEN - overlap_chars)

    pieces: list[str] = []
    for sentence in _split_sentences(text):
        if len(sentence) > content_chars:
            pieces.extend(_hard_split(sentence, content_chars))
        else:
            pieces.append(sentence)

    chunks: list[Chunk] = []
    current: list[str] = []
    current_len = 0

    def flush() -> None:
        nonlocal current, current_len
        joined = " ".join(current).strip()
        if joined:
            chunks.append(Chunk(len(chunks), joined, estimate_tokens(joined)))
        current, current_len = [], 0

    for piece in pieces:
        piece_len = len(piece) + (1 if current else 0)
        if current and current_len + piece_len > content_chars:
            flush()
            tail = _overlap_tail(chunks[-1].text, overlap_chars)
            tail_len = sum(len(w) for w in tail) + max(0, len(tail) - 1)
            if tail_len + piece_len > content_chars:
                tail, tail_len = [], 0
            current, current_len = tail, tail_len
        current.append(piece)
        current_len += piece_len
    flush()

    # Re-index chunks (flush logic ensures no accidental empty chunks).
    return [Chunk(i, c.text, c.token_count) for i, c in enumerate(chunks)]
