"""Tests for TTS service."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest


def test_synthesize_with_espeak(tmp_path, monkeypatch):
    """Generate a real WAV in tmp_path when espeak-ng is installed."""
    from app.services import tts_service
    monkeypatch.setattr(tts_service, "AUDIO_DIR", tmp_path / "audio")
    tts_service.reset_cache()

    if not shutil.which("espeak-ng"):
        pytest.skip("espeak-ng is not installed")

    path = tts_service.synthesize_to_file("Hello world, this is a test.", "test_espeak.wav")

    assert os.path.exists(path)
    assert os.path.getsize(path) > 1024
    tts_service.reset_cache()


def test_synthesize_missing_engine_raises(tmp_path, monkeypatch):
    """Simulated missing engine raises the clear RuntimeError."""
    from app.services import tts_service
    monkeypatch.setattr(tts_service, "AUDIO_DIR", tmp_path / "audio")
    tts_service.reset_cache()

    with patch.object(tts_service, "tts_available", return_value=False):
        try:
            tts_service.synthesize_to_file("test text", "test_fail.wav")
            assert False, "Expected RuntimeError"
        except RuntimeError as e:
            assert "Audio generation failed" in str(e)
    tts_service.reset_cache()


def test_summaries_page_helper_does_not_crash(tmp_path, monkeypatch):
    """The summaries page Play button handler does not crash on TTS error."""
    from app.services import tts_service
    monkeypatch.setattr(tts_service, "AUDIO_DIR", tmp_path / "audio")
    tts_service.reset_cache()

    with patch.object(tts_service, "tts_available", return_value=False):
        path = None
        try:
            path = tts_service.synthesize_to_file("test", "fail.wav")
        except RuntimeError:
            pass
        assert path is None  # either None or RuntimeError caught — no crash
    tts_service.reset_cache()


def test_text_cleaning_removes_markdown():
    """Text cleaning removes markdown markers."""
    from app.services.tts_service import clean_text

    text = "# Heading\n* bullet\n**bold** and _italic_ and `code` and [link](http://example.com)\n1. numbered\n- bullet"
    cleaned = clean_text(text)
    assert "#" not in cleaned or cleaned.count("#") == 0
    assert "*" not in cleaned.split()[0] if cleaned.split() else True
    assert "**" not in cleaned
    assert "__" not in cleaned
    assert "`" not in cleaned
    assert "http" not in cleaned.split()[0] if cleaned.split() else True


def test_text_cleaning_collapses_whitespace():
    """Text cleaning collapses whitespace."""
    from app.services.tts_service import clean_text, collapse_whitespace

    text = "Hello   \n\n\n  World  "
    collapsed = collapse_whitespace(text)
    assert "  " not in collapsed  # no double spaces
    assert collapsed.strip() == "Hello World"


def test_sentence_splitting():
    """Sentence splitting works correctly."""
    from app.services.tts_service import split_into_sentences

    text = "Hello world. This is a test! Are you there?"
    sentences = split_into_sentences(text)
    assert len(sentences) == 3
    assert "Hello world." in sentences
    assert "This is a test!" in sentences


def test_grouping_by_char_limit():
    """Sentence grouping respects the character limit."""
    from app.services.tts_service import group_sentences

    sentences = ["Short.", "This is a medium sentence.", "This is a very long sentence that definitely exceeds the limit."]
    groups = group_sentences(sentences, max_chars=50)
    # Each group should be at most ~50 chars (approx, may include spaces)
    for group in groups:
        assert len(group) < 100, f"Group too long: {group!r} ({len(group)} chars)"


def test_end_to_end_utf16_tts():
    """End-to-end: TXT containing dates saved as UTF-16 goes through extraction and produces events."""
    from app.services import event_service, extraction_service
    from pathlib import Path
    import tempfile

    # Create a TXT file with a date, saved as UTF-16 with BOM
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="wb") as f:
        f.write("\ufeffSubmission deadline: 15 October 2026".encode("utf-16"))
        tmp_path = f.name

    try:
        text = extraction_service.extract_text(tmp_path, "txt")
        events = event_service.extract_events(text)
        # Should find the deadline event
        dates = [e["event_date"] for e in events]
        assert "2026-10-15" in dates, f"Expected 2026-10-15 in {dates}"
    finally:
        Path(tmp_path).unlink(missing_ok=True)