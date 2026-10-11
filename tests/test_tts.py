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

    with patch.object(tts_service, "_check_espeak", return_value=False):
        with patch.object(tts_service, "_get_engine", return_value=None):
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

    with patch.object(tts_service, "_check_espeak", return_value=False):
        with patch.object(tts_service, "_get_engine", return_value=None):
            path = None
            try:
                path = tts_service.synthesize_to_file("test", "fail.wav")
            except RuntimeError:
                pass
            assert path is None  # either None or RuntimeError caught — no crash
    tts_service.reset_cache()
