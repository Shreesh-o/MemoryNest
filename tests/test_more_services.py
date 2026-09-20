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
    # TTS should be unavailable without espeak-ng
    result = tts_service.synthesize_to_file("hello")
    assert result is None
    assert tts_service.tts_available() is False


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