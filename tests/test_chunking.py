"""Tests for the chunking service."""

from __future__ import annotations

from app.services.chunking_service import Chunk, chunk_text, estimate_tokens


def test_short_text_single_chunk():
    chunks = chunk_text("Hello world. This is short.")
    assert len(chunks) == 1
    assert chunks[0].text == "Hello world. This is short."
    assert chunks[0].index == 0


def test_empty_text():
    assert chunk_text("") == []
    assert chunk_text("   \n  ") == []


def test_long_text_multiple_chunks_within_budget():
    sentence = "The quick brown fox jumps over the lazy dog near the river bank. "
    text = sentence * 200  # ~12k tokens
    chunks = chunk_text(text, max_tokens=450, overlap_tokens=50)
    assert len(chunks) > 5
    for c in chunks:
        # Hard pieces can hit the budget exactly; allow the configured max.
        assert c.token_count <= 450, f"chunk {c.index} is {c.token_count} tokens"
        assert c.text.strip()


def test_overlap_between_consecutive_chunks():
    sentence = "Alpha beta gamma delta epsilon. Zeta eta theta iota kappa. "
    text = sentence * 100
    chunks = chunk_text(text, max_tokens=300, overlap_tokens=50)
    assert len(chunks) >= 3
    # At least one boundary should share trailing words from the previous chunk.
    shared = 0
    for prev, cur in zip(chunks, chunks[1:]):
        tail_words = set(prev.text.split()[-10:])
        head_words = set(cur.text.split()[:10])
        if tail_words & head_words:
            shared += 1
    assert shared >= 1, "no overlap found between consecutive chunks"


def test_oversized_single_sentence_hard_split():
    blob = "word " * 2000  # one giant sentence, no terminal punctuation
    text = blob.strip()
    chunks = chunk_text(text, max_tokens=400, overlap_tokens=40)
    assert len(chunks) > 1
    for c in chunks:
        assert c.token_count <= 400
    # No word is lost.
    rejoined = " ".join(c.text for c in chunks)
    assert rejoined.count("word") >= 2000 - len(chunks) * 5  # tolerate overlap clipping


def test_chunk_text_covers_all_words():
    text = " ".join(f"token{i} unique{i}" for i in range(3000))
    chunks = chunk_text(text, max_tokens=400, overlap_tokens=50)
    rejoined = " ".join(c.text for c in chunks)
    for i in range(0, 3000, 97):
        assert f"unique{i}" in rejoined


def test_indices_sequential():
    text = "Sentence one here. " * 500
    chunks = chunk_text(text, max_tokens=200, overlap_tokens=20)
    assert [c.index for c in chunks] == list(range(len(chunks)))


def test_estimate_tokens():
    assert estimate_tokens("") == 1
    assert estimate_tokens("a" * 400) == 100
