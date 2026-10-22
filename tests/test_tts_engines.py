"""Tests for TTS engines and fallback order."""

from __future__ import annotations

import os
import wave
from pathlib import Path
from unittest.mock import patch

import pytest

from app.services import tts_service


def _create_dummy_wav(path: str) -> None:
    """Helper to create a valid WAV file > 1024 bytes."""
    p = Path(path).with_suffix(".wav")
    p.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(p), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        # Write ~1500 bytes of audio frames
        w.writeframes(b"\x00\x00" * 750)


def test_engine_fallback_edge_fails_to_espeak(tmp_path, monkeypatch):
    """When edge-tts fails (e.g. timeout/network error) and piper is unavailable, fallback to espeak-ng."""
    monkeypatch.setattr(tts_service, "AUDIO_DIR", tmp_path / "audio")
    monkeypatch.setenv("TTS_ENGINE", "auto")
    tts_service.reset_cache()

    # Ensure piper is skipped
    monkeypatch.setattr(tts_service, "_piper_model_exists", lambda *args, **kwargs: False)

    # Fake edge failure
    edge_called = []
    def fake_synthesize_edge(text, output_path, timeout=8.0):
        edge_called.append(True)
        return False

    # Fake espeak-ng success
    espeak_called = []
    def fake_synthesize_espeak(text, output_path):
        espeak_called.append(True)
        _create_dummy_wav(output_path)
        return True

    monkeypatch.setattr(tts_service, "synthesize_with_edge", fake_synthesize_edge)
    monkeypatch.setattr(tts_service, "synthesize_with_espeak_ng", fake_synthesize_espeak)

    out_path, engine = tts_service.synthesize_with_engine("Hello fallback test")

    assert edge_called, "edge-tts should have been attempted"
    assert espeak_called, "espeak-ng should have been called as fallback"
    assert engine == "espeak-ng"
    assert os.path.exists(out_path)
    assert os.path.getsize(out_path) > 1024


def test_engine_forced_espeak(tmp_path, monkeypatch):
    """TTS_ENGINE=espeak forces espeak-ng directly, skipping piper and edge."""
    monkeypatch.setattr(tts_service, "AUDIO_DIR", tmp_path / "audio")
    monkeypatch.setenv("TTS_ENGINE", "espeak")
    tts_service.reset_cache()

    piper_called = []
    def fake_synthesize_piper(text, output_path, voice=None):
        piper_called.append(True)
        _create_dummy_wav(output_path)
        return True

    edge_called = []
    def fake_synthesize_edge(text, output_path, timeout=8.0):
        edge_called.append(True)
        _create_dummy_wav(output_path)
        return True

    espeak_called = []
    def fake_synthesize_espeak(text, output_path):
        espeak_called.append(True)
        _create_dummy_wav(output_path)
        return True

    monkeypatch.setattr(tts_service, "synthesize_with_piper", fake_synthesize_piper)
    monkeypatch.setattr(tts_service, "synthesize_with_edge", fake_synthesize_edge)
    monkeypatch.setattr(tts_service, "synthesize_with_espeak_ng", fake_synthesize_espeak)

    out_path, engine = tts_service.synthesize_with_engine("Hello force espeak test")

    assert not piper_called, "piper should not be called when TTS_ENGINE=espeak"
    assert not edge_called, "edge-tts should not be called when TTS_ENGINE=espeak"
    assert espeak_called, "espeak-ng should be called directly"
    assert engine == "espeak-ng"
    assert os.path.exists(out_path)


def test_real_generation_tts(tmp_path, monkeypatch):
    """Real synthesis test: produces valid audio file > 1KB or is skipped if no engine is installed."""
    monkeypatch.setattr(tts_service, "AUDIO_DIR", tmp_path / "audio")
    tts_service.reset_cache()

    if not tts_service.tts_available():
        pytest.skip("No TTS engine installed in environment")

    path, engine = tts_service.synthesize_with_engine(
        "MemoryNest intelligent personal memory assistant audio test."
    )

    assert os.path.exists(path), f"Audio file not found at {path}"
    assert os.path.getsize(path) > 1024, f"Audio file too small: {os.path.getsize(path)} bytes"
    assert engine in ("piper", "edge", "espeak-ng", "pyttsx3")
