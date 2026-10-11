"""TTS service: espeak-ng CLI first, pyttsx3 fallback."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import uuid
import wave
from pathlib import Path

from app.utils.config import AUDIO_DIR

logger = logging.getLogger(__name__)

_tts_engine = None
_tts_available = None
_espeak_available = None

MAX_CHUNK = 500


def _check_espeak() -> bool:
    global _espeak_available
    if _espeak_available is None:
        _espeak_available = shutil.which("espeak-ng") is not None
    return _espeak_available


def _get_engine():
    global _tts_engine, _tts_available
    if _tts_available is False:
        return None
    if _tts_engine is None:
        try:
            import pyttsx3
            _tts_engine = pyttsx3.init()
            _tts_engine.getProperty("voices")
        except Exception as e:
            _tts_engine = None
            _tts_available = False
            logger.warning("pyttsx3 init failed: %s", e)
    return _tts_engine


def tts_available() -> bool:
    return _check_espeak() or _get_engine() is not None


def _synthesize_espeak(text: str, out_path: str) -> bool:
    """Use espeak-ng CLI to synthesize text to a WAV file."""
    try:
        result = subprocess.run(
            ["espeak-ng", "-w", out_path],
            input=text,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            logger.error("espeak-ng failed (code %d): %s", result.returncode, result.stderr[:200])
            return False
        if not os.path.exists(out_path) or os.path.getsize(out_path) < 1024:
            logger.error("espeak-ng produced no valid output: %s", out_path)
            return False
        return True
    except subprocess.TimeoutExpired:
        logger.error("espeak-ng timed out for text length %d", len(text))
        return False
    except Exception as e:
        logger.error("espeak-ng exception: %s", e)
        return False


def _synthesize_pyttsx3(text: str, out_path: str) -> bool:
    """Fallback: use pyttsx3 to synthesize text to a WAV file."""
    engine = _get_engine()
    if engine is None:
        return False
    try:
        engine.save_to_file(text, out_path)
        engine.runAndWait()
        if not os.path.exists(out_path) or os.path.getsize(out_path) < 1024:
            logger.error("pyttsx3 produced no valid output: %s", out_path)
            return False
        return True
    except Exception as e:
        logger.error("pyttsx3 synthesis failed: %s", e)
        return False


def _merge_wavs(wav_paths: list[str], merged_path: str) -> bool:
    """Merge multiple WAV files into one using the wave module."""
    if len(wav_paths) == 1:
        shutil.copy2(wav_paths[0], merged_path)
        return True
    with wave.open(wav_paths[0], "rb") as w:
        params = w.getparams()
    with wave.open(merged_path, "wb") as out_wav:
        out_wav.setparams(params)
        for wav_path in wav_paths:
            with wave.open(wav_path, "rb") as w:
                out_wav.writeframes(w.readframes(w.getnframes()))
    return True


def synthesize_to_file(text: str, filename: str | None = None) -> str:
    """Convert text to speech and save as WAV. Returns file path.

    Raises RuntimeError if audio generation fails.
    """
    if filename is None:
        filename = f"tts_{uuid.uuid4().hex[:8]}.wav"
    path = AUDIO_DIR / filename
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    # Split long text into chunks and merge
    chunks = [text[i:i + MAX_CHUNK] for i in range(0, len(text), MAX_CHUNK)]
    chunk_paths: list[str] = []
    chunk_dir = AUDIO_DIR / f"chunks_{filename.rsplit('.', 1)[0]}"

    # Try espeak-ng first
    if _check_espeak():
        chunk_dir.mkdir(parents=True, exist_ok=True)
        for i, chunk in enumerate(chunks):
            chunk_path = str(chunk_dir / f"chunk_{i}.wav")
            if _synthesize_espeak(chunk, chunk_path):
                chunk_paths.append(chunk_path)
        if chunk_paths:
            if _merge_wavs(chunk_paths, str(path)):
                _cleanup_chunks(chunk_dir)
                if path.exists() and path.stat().st_size > 1024:
                    return str(path)
            _cleanup_chunks(chunk_dir)

    # Fallback to pyttsx3 (no chunk merge for simplicity — synthesize whole text)
    if _synthesize_pyttsx3(text, str(path)):
        if path.exists() and path.stat().st_size > 1024:
            return str(path)

    raise RuntimeError(
        "Audio generation failed: no TTS engine produced a valid WAV file. "
        "Install espeak-ng: pacman -S espeak-ng"
    )


def _cleanup_chunks(chunk_dir: Path) -> None:
    """Remove temporary chunk files."""
    import shutil as _shutil
    try:
        _shutil.rmtree(chunk_dir, ignore_errors=True)
    except Exception:
        pass


def reset_cache() -> None:
    """Reset cached engine state (for testing)."""
    global _tts_engine, _tts_available, _espeak_available
    _tts_engine = None
    _tts_available = None
    _espeak_available = None
