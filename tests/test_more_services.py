"""Tests for summary, TTS, event extraction, and email services."""

from __future__ import annotations

import os

import pytest

from app.services import summary_service, tts_service, event_service, email_service


def test_summarize_short(monkeypatch):
    monkeypatch.setenv("MOCK_LLM", "1")
    text = "This is a short document about revenue growth. Revenue was $1.2M."
    summary = summary_service.summarize_document(text)
    assert isinstance(summary, str)
    assert "mock" in summary.lower() or "revenue" in summary.lower()


def test_summarize_long_map_reduce(monkeypatch):
    monkeypatch.setenv("MOCK_LLM", "1")
    # Create a long text that will be split into multiple chunks
    base = "Sentence about project alpha. " * 500
    text = base + " Budget is $50,000. Deadline is 2026-12-31."
    summary = summary_service.summarize_document(text, max_chunk_tokens=200)
    assert isinstance(summary, str)
    assert len(summary) > 0


def test_tts_unavailable(monkeypatch):
    # Mock pyttsx3.init to raise an exception, simulating missing espeak-ng
    import app.services.tts_service as tts_mod
    monkeypatch.setattr(tts_mod, "_get_engine", lambda: None)
    monkeypatch.setattr(tts_mod, "_tts_engine", None)
    monkeypatch.setattr(tts_mod, "_tts_available", False)
    monkeypatch.setattr(tts_mod, "_check_espeak", lambda: False)
    tts_mod.reset_cache()

    try:
        tts_service.synthesize_to_file("hello")
        assert False, "Expected RuntimeError"
    except RuntimeError as e:
        assert "Audio generation failed" in str(e)


def test_tts_available(monkeypatch):
    # When espeak-ng is available, synthesis should produce a file
    # This test runs with real pyttsx3 (espeak-ng is installed on the system)
    tts_service.reset_cache()
    if tts_service.tts_available():
        result = tts_service.synthesize_to_file("test")
        assert isinstance(result, str)
        assert result.endswith(".wav")
    else:
        pytest.skip("espeak-ng not available in this environment")


def test_event_extraction_regex():
    text = (
        "The meeting is on 2026-10-15 at 10 AM. "
        "Project deadline is Oct 31, 2026. "
        "No date here."
    )
    events = event_service.extract_events(text)
    assert len(events) >= 2
    dates = [e["event_date"] for e in events]
    assert "2026-10-15" in dates
    assert "2026-10-31" in dates
    for e in events:
        assert e["event_text"]
        assert e["raw_date"]


def test_event_extraction_no_dates():
    events = event_service.extract_events("This text has no dates at all.")
    # With MOCK_LLM=1, LLM fallback returns mock response which may not be valid JSON
    # So we just verify it doesn't crash
    assert isinstance(events, list)


def test_event_extraction_indian_date_formats(monkeypatch):
    """All 8 lines from BUG 2 produce events with the correct date."""
    from datetime import datetime
    from unittest.mock import patch

    lines = [
        "Submission deadline: 15 October 2026",
        "Project review on 20 Oct 2026 at 3 PM",
        "Exam: 25/10/2026",
        "Report due 2026-11-02",
        "Viva on Monday 26th October",
        "Fee payment last date - 5th Nov",
        "Meeting tomorrow at 5 pm",
        "Assignment submission by October 30",
    ]
    expected_dates = [
        "2026-10-15",
        "2026-10-20",
        "2026-10-25",
        "2026-11-02",
        "2026-10-26",
        "2026-11-05",
        "2026-10-13",  # tomorrow from 2026-10-12
        "2026-10-30",
    ]

    text = "\n".join(lines)
    with patch.object(event_service, "datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 10, 12)
        events = event_service.extract_events(text)

    assert len(events) == 8, f"Expected 8 events, got {len(events)}"

    found_dates = [e["event_date"] for e in events]
    for expected, line in zip(expected_dates, lines):
        assert expected in found_dates, f"Missing date {expected} for line: {line}"


def test_email_config_missing(monkeypatch):
    monkeypatch.delenv("EMAIL_USERNAME", raising=False)
    monkeypatch.delenv("EMAIL_APP_PASSWORD", raising=False)
    monkeypatch.delenv("RECIPIENT_EMAIL", raising=False)
    ok, msg = email_service.check_email_config()
    assert ok is False
    assert "Missing" in msg


def test_send_reminder_missing_config(monkeypatch):
    monkeypatch.delenv("EMAIL_USERNAME", raising=False)
    ok, detail = email_service.send_reminder_email("Test", "Body")
    assert ok is False
    assert "not configured" in detail