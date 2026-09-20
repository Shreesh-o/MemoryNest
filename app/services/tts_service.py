"""TTS service using pyttsx3 (offline, requires espeak-ng)."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from app.utils.config import AUDIO_DIR


_tts_engine = None
_tts_available = None


def _get_engine():
    global _tts_engine, _tts_available
    if _tts_available is False:
        return None
    if _tts_engine is None:
        try:
            import pyttsx3
            _tts_engine = pyttsx3.init()
            # Test if it actually works
            _tts_engine.getProperty("voices")
        except Exception as e:
            _tts_engine = None
            _tts_available = False
            print(f"[TTS] pyttsx3 init failed: {e}. Install espeak-ng: pacman -S espeak-ng")
    return _tts_engine


def tts_available() -> bool:
    return _get_engine() is not None


def synthesize_to_file(text: str, filename: str | None = None) -> str | None:
    """Convert text to speech and save as WAV. Returns file path or None on failure."""
    engine = _get_engine()
    if engine is None:
        return None
    if filename is None:
        filename = f"tts_{uuid.uuid4().hex[:8]}.wav"
    path = AUDIO_DIR / filename
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    try:
        engine.save_to_file(text, str(path))
        engine.runAndWait()
        return str(path)
    except Exception as e:
        print(f"[TTS] synthesis failed: {e}")
        return None