"""TTS service: espeak-ng CLI, piper (neural), pyttsx3 fallback.

Features:
- Text cleaning (markdown removal, sentence grouping, whitespace collapsing)
- Wav merging with silence between groups
- Engine selection via TTS_ENGINE env var (auto, piper, espeak, pyttsx3)
- Per-engine tuning and sample-rate/channel consistency checks
"""

from __future__ import annotations

import io
import logging
import os
import re
import shutil
import subprocess
import struct
import wave
from pathlib import Path
from typing import List, Tuple, Optional

from app.utils.config import AUDIO_DIR

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Engine configuration
# ---------------------------------------------------------------------------

TTS_ENGINE = os.environ.get("TTS_ENGINE", "auto").lower()
TTS_VOICE = os.environ.get("TTS_VOICE", "en_US-lessac-medium")

VALID_ENGINES = {"auto", "piper", "edge", "espeak", "pyttsx3"}

# ---------------------------------------------------------------------------
# Text cleaning
# ---------------------------------------------------------------------------

_MARKDOWN_RE = re.compile(r"[#*_`]|https?://\S+|---|\d+\.")

_BULLET_DASH_RE = re.compile(r"^\s*[-*•]\s+", re.MULTILINE)
_NUMBERED_LIST_RE = re.compile(r"^\s*\d+[\.\)]\s+", re.MULTILINE)

_LINK_RE = re.compile(r"https?://\S+|\[.*?\]\(.*?\)")


def _strip_markdown(text: str) -> str:
    """Remove markdown formatting: #, *, _, backticks, links, bullet dashes, numbers."""
    text = _LINK_RE.sub("", text)
    text = _MARKDOWN_RE.sub("", text)
    text = _BULLET_DASH_RE.sub("", text)
    text = _NUMBERED_LIST_RE.sub("", text)
    return text


def collapse_whitespace(text: str) -> str:
    """Collapse multiple spaces/newlines into single spaces, but preserve sentence boundaries."""
    # Replace newlines with a space, then collapse multiple spaces
    text = text.replace("\n", " ")
    text = re.sub(r"[ \t]+", " ", text)
    return text


def clean_text(text: str) -> str:
    """Full text cleaning pipeline: strip markdown, collapse whitespace, normalize newlines."""
    text = _strip_markdown(text)
    text = collapse_whitespace(text)
    return text


def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences using a regex-based approach.

    Sentence endings are . ! ? followed by whitespace or end-of-string.
    """
    # Simple sentence splitter: split on . ! ? followed by space or EOL
    sentences = re.split(r"(?<=[.!?])\s+", text)
    # Filter out empty strings and very short fragments
    sentences = [s.strip() for s in sentences if s.strip()]
    return sentences


def group_sentences(sentences: List[str], max_chars: int = 400) -> List[str]:
    """Group sentences into chunks, each chunk <= max_chars (approx).

    Groups are formed by adding sentences until adding the next would exceed
    max_chars. Word boundaries are preferred but not guaranteed.
    """
    if not sentences:
        return []

    groups: List[str] = []
    current: List[str] = []
    current_len = 0

    for sentence in sentences:
        s_len = len(sentence)
        if current_len + s_len > max_chars and current:
            groups.append(" ".join(current))
            current = [sentence]
            current_len = s_len
        else:
            current.append(sentence)
            current_len += s_len + 1  # +1 for space

    if current:
        groups.append(" ".join(current))

    return groups


# ---------------------------------------------------------------------------
# WAV file operations
# ---------------------------------------------------------------------------

def _read_wav_info(path: Path) -> Tuple[int, int, int]:
    """Read nchannels, sampwidth, framerate from a WAV file.

    Returns (nchannels, sampwidth, framerate).
    """
    with wave.open(str(path), "rb") as w:
        return w.getnchannels(), w.getsampwidth(), w.getframerate()


def _ensure_same_format(wav_paths: List[Path]) -> None:
    """Verify all WAV files have the same format; raise RuntimeError if not.

    If formats differ, attempt automatic resample using Python wave module
    (limited) or raise a clear error.
    """
    if len(wav_paths) <= 1:
        return

    # Read first file's format
    nchannels, sampwidth, framerate = _read_wav_info(wav_paths[0])

    for path in wav_paths[1:]:
        cn, sp, fr = _read_wav_info(path)
        if cn != nchannels or sp != sampwidth or fr != framerate:
            raise RuntimeError(
                f"WAV format mismatch: {wav_paths[0].name} "
                f"({nchannels}ch, {sampwidth}samp, {framerate}Hz) vs "
                f"{path.name} ({cn}ch, {sp}samp, {fr}Hz). "
                "All WAVs must have identical sample rate, bit depth, and channels "
                "before merging. Convert each group separately."
            )


def _add_silence_ms(wav_path: Path, silence_ms: int) -> Path:
    """Append 'silence_ms' milliseconds of silence to the end of a WAV file.

    Returns the path (same object, modified in-place where possible).
    """
    nchannels, sampwidth, framerate = _read_wav_info(wav_path)
    n_frames = int(silence_ms * framerate / 1000)
    # Generate silence samples
    silence_samples = b"\x00" * (n_frames * sampwidth * nchannels)
    with wave.open(str(wav_path), "ab") as w:
        w.setnchannels(nchannels)
        w.setsampwidth(sampwidth)
        w.setframerate(framerate)
        w.writeframes(silence_samples)
    return wav_path


def merge_wavs_with_silence(
    wav_paths: List[Path], output_path: Path, silence_ms: int = 250
) -> None:
    """Merge multiple WAV files into one, with silence_ms ms gap between each.

    All WAVs must have the same sample rate, bit depth, and channels.
    Silence of 'silence_ms' milliseconds is appended after each file except the last.
    """
    # Ensure consistent format
    _ensure_same_format(wav_paths)

    # Read first file params
    nchannels, sampwidth, framerate = _read_wav_info(wav_paths[0])

    # Read all original frames
    all_frames: List[bytes] = []
    for p in wav_paths:
        with wave.open(str(p), "rb") as w:
            nf = w.getnframes()
            frames = w.readframes(nf)
            all_frames.append(frames)

    with wave.open(str(output_path), "wb") as out:
        out.setnchannels(nchannels)
        out.setsampwidth(sampwidth)
        out.setframerate(framerate)

        for i, frames in enumerate(all_frames):
            out.writeframes(frames)
            if i < len(all_frames) - 1:
                # Write silence buffer
                n_frames = int(silence_ms * framerate / 1000)
                silence_buf = b"\x00" * (n_frames * sampwidth * nchannels)
                out.writeframes(silence_buf)


def synthesize_with_piper(
    text: str, output_path: str, voice: str | None = None
) -> bool:
    """Synthesize text using Piper TTS engine.

    Requires: piper-tts and an onnx voice model at models/piper/<voice>.onnx
    """
    try:
        import piper  # noqa: F401
    except ImportError:
        logger.warning("piper-tts not installed")
        return False

    v = voice or os.environ.get("TTS_VOICE", "en_US-lessac-medium")
    candidates = [
        Path("models/piper") / f"{v}.onnx",
        Path("models/piper") / v,
        Path(v),
    ]
    model_path = next((p for p in candidates if p.exists() and p.is_file()), None)
    if not model_path:
        logger.warning("Piper model not found for voice %s in %s", v, candidates)
        return False

    try:
        from piper import PiperVoice
        voice_obj = PiperVoice.load(str(model_path))
        wav_target = str(Path(output_path).with_suffix(".wav"))
        with wave.open(wav_target, "wb") as wav_file:
            voice_obj.synthesize_wav(text, wav_file)

        if Path(wav_target).exists() and Path(wav_target).stat().st_size > 1024:
            logger.info("Piper synthesized %s (%d bytes)", wav_target, Path(wav_target).stat().st_size)
            return True
        logger.error("Piper produced no valid output or file < 1KB")
        return False
    except Exception as e:
        logger.error("Piper synthesis failed: %s", e)
        return False


def synthesize_with_edge(
    text: str, output_path: str, timeout: float = 8.0
) -> bool:
    """Synthesize text using edge-tts engine.

    Tries en-IN-NeerjaNeural first, falls back to en-US-AriaNeural.
    Converts MP3 to WAV with ffmpeg if available; otherwise keeps MP3.
    """
    try:
        import edge_tts
    except ImportError:
        logger.warning("edge-tts not installed")
        return False

    import asyncio
    import tempfile

    voices = ["en-IN-NeerjaNeural", "en-US-AriaNeural"]
    has_ffmpeg = shutil.which("ffmpeg") is not None

    for voice in voices:
        tmp_mp3 = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_f:
                tmp_mp3 = tmp_f.name

            async def _run_edge(v: str, out_f: str):
                communicate = edge_tts.Communicate(text, v)
                await communicate.save(out_f)

            asyncio.run(asyncio.wait_for(_run_edge(voice, tmp_mp3), timeout=timeout))

            if Path(tmp_mp3).exists() and Path(tmp_mp3).stat().st_size > 1024:
                if has_ffmpeg:
                    wav_target = str(Path(output_path).with_suffix(".wav"))
                    res = subprocess.run(
                        ["ffmpeg", "-y", "-i", tmp_mp3, "-ar", "16000", "-ac", "1", wav_target],
                        capture_output=True,
                        timeout=15,
                    )
                    if res.returncode == 0 and Path(wav_target).exists() and Path(wav_target).stat().st_size > 1024:
                        logger.info("edge-tts (%s) converted to WAV: %s", voice, wav_target)
                        return True
                else:
                    mp3_target = str(Path(output_path).with_suffix(".mp3"))
                    shutil.copy2(tmp_mp3, mp3_target)
                    if Path(mp3_target).exists() and Path(mp3_target).stat().st_size > 1024:
                        logger.info("edge-tts (%s) saved MP3 (no ffmpeg): %s", voice, mp3_target)
                        return True
        except Exception as e:
            logger.warning("edge-tts failed with voice %s: %s", voice, e)
        finally:
            if tmp_mp3 and Path(tmp_mp3).exists():
                try:
                    Path(tmp_mp3).unlink(missing_ok=True)
                except OSError:
                    pass

    return False


def synthesize_with_espeak_ng(
    text: str, output_path: str,
) -> bool:
    """Synthesize text using espeak-ng CLI.

    Tuning: -s 150, -p 45, -g 4, voice en-us+f3 (fallback to en-gb, en).
    """
    if shutil.which("espeak-ng") is None:
        logger.warning("espeak-ng not installed")
        return False

    voice_variants = ["en-us+f3", "en-gb", "en"]
    wav_target = str(Path(output_path).with_suffix(".wav"))

    for voice in voice_variants:
        try:
            cmd = [
                "espeak-ng",
                "-v", voice,
                "-s", "150",
                "-p", "45",
                "-g", "4",
                "-w", wav_target,
            ]
            res = subprocess.run(
                cmd, input=text, capture_output=True, text=True, timeout=60
            )
            if res.returncode == 0 and Path(wav_target).exists() and Path(wav_target).stat().st_size > 1024:
                logger.info("espeak-ng (%s) succeeded: %s (%d bytes)", voice, wav_target, Path(wav_target).stat().st_size)
                return True
        except Exception as e:
            logger.error("espeak-ng voice %s failed: %s", voice, e)
            if Path(wav_target).exists():
                Path(wav_target).unlink(missing_ok=True)

    return False


def synthesize_with_pyttsx3(
    text: str, output_path: str
) -> bool:
    """Fallback synthesis using pyttsx3.

    Returns True if successful and output > 1 KB.
    """
    try:
        import pyttsx3
    except ImportError:
        logger.warning("pyttsx3 not installed")
        return False

    try:
        wav_target = str(Path(output_path).with_suffix(".wav"))
        engine = pyttsx3.init()
        engine.save_to_file(text, wav_target)
        engine.runAndWait()
        if Path(wav_target).exists() and Path(wav_target).stat().st_size > 1024:
            logger.info("pyttsx3 synthesized %s (%d bytes)", wav_target, Path(wav_target).stat().st_size)
            return True
        else:
            logger.error("pyttsx3 produced no valid output")
            return False
    except Exception as e:
        logger.error("pyttsx3 synthesis failed: %s", e)
        return False


# ---------------------------------------------------------------------------
# Main synthesis entry point
# ---------------------------------------------------------------------------

def _select_engine(engine_name: str | None = None) -> str:
    """Select and validate the TTS engine.

    Returns the engine name that will be used.
    """
    engine = engine_name or os.environ.get("TTS_ENGINE", "auto")
    engine = engine.lower()
    if engine not in VALID_ENGINES:
        logger.warning("Invalid TTS_ENGINE '%s', defaulting to 'auto'", engine)
        return "auto"
    return engine


def _piper_model_exists(voice: str | None = None) -> bool:
    """Check if a piper voice model is present."""
    v = voice or os.environ.get("TTS_VOICE", "en_US-lessac-medium")
    candidates = [
        Path("models/piper") / f"{v}.onnx",
        Path("models/piper") / v,
        Path(v),
    ]
    return any(p.exists() and p.is_file() for p in candidates)


def synthesize_with_engine(text: str, filename: str | None = None) -> Tuple[str, str]:
    """Convert text to speech and return (file_path, engine_name).

    Engine fallback order:
    1. If TTS_ENGINE == 'espeak': forces espeak-ng -> pyttsx3.
    2. If TTS_ENGINE == 'piper': piper -> edge -> espeak-ng -> pyttsx3.
    3. If TTS_ENGINE == 'edge': edge -> espeak-ng -> pyttsx3.
    4. Default 'auto': piper (if model exists) -> edge (8s timeout) -> espeak-ng -> pyttsx3.
    """
    clean = clean_text(text)
    if not clean.strip():
        raise RuntimeError("Audio generation failed: no valid text after cleaning.")

    if not tts_available():
        raise RuntimeError(
            "Audio generation failed: no TTS engine is available. "
            "Install piper-tts with a voice model, edge-tts, "
            "or ensure espeak-ng or pyttsx3 is installed."
        )

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    if filename is None:
        base_name = f"tts_{os.urandom(4).hex()}"
        target_path = str(AUDIO_DIR / f"{base_name}.wav")
    else:
        target_path = str(Path(filename))

    configured = _select_engine()

    # Determine order of engines to attempt
    if configured == "espeak":
        order = ["espeak", "pyttsx3"]
    elif configured == "piper":
        order = ["piper", "edge", "espeak", "pyttsx3"]
    elif configured == "edge":
        order = ["edge", "espeak", "pyttsx3"]
    elif configured == "pyttsx3":
        order = ["pyttsx3", "espeak"]
    else:  # auto
        order = []
        if _piper_model_exists():
            order.append("piper")
        order.extend(["edge", "espeak", "pyttsx3"])

    for eng in order:
        if eng == "piper":
            if synthesize_with_piper(clean, target_path):
                actual_path = _find_generated_file(target_path)
                if actual_path:
                    return actual_path, "piper"
        elif eng == "edge":
            if synthesize_with_edge(clean, target_path, timeout=8.0):
                actual_path = _find_generated_file(target_path)
                if actual_path:
                    return actual_path, "edge"
        elif eng == "espeak":
            if synthesize_with_espeak_ng(clean, target_path):
                actual_path = _find_generated_file(target_path)
                if actual_path:
                    return actual_path, "espeak-ng"
        elif eng == "pyttsx3":
            if synthesize_with_pyttsx3(clean, target_path):
                actual_path = _find_generated_file(target_path)
                if actual_path:
                    return actual_path, "pyttsx3"

    raise RuntimeError(
        f"Audio generation failed: no TTS engine produced a valid audio file (>1 KB). "
        f"Engine configured: {configured}."
    )


def _find_generated_file(target_path: str) -> Optional[str]:
    """Find the output file whether saved as .wav or .mp3."""
    p = Path(target_path)
    for candidate in [p, p.with_suffix(".wav"), p.with_suffix(".mp3")]:
        if candidate.exists() and candidate.stat().st_size > 1024:
            return str(candidate)
    return None


def synthesize_to_file(text: str, filename: str | None = None) -> str:
    """Convert text to speech and return the output path."""
    path, _ = synthesize_with_engine(text, filename)
    return path


def tts_available() -> bool:
    """Check if any TTS engine is available.

    Returns True if at least one engine (piper, edge, espeak-ng, or pyttsx3) can be used.
    """
    # Piper
    try:
        import piper  # noqa: F401
        if _piper_model_exists():
            return True
    except ImportError:
        pass

    # Edge
    try:
        import edge_tts  # noqa: F401
        return True
    except ImportError:
        pass

    # espeak-ng
    if shutil.which("espeak-ng") is not None:
        return True

    # pyttsx3
    try:
        import pyttsx3  # noqa: F401
        return True
    except ImportError:
        pass

    return False


def reset_cache() -> None:
    """Reset any cached state (for testing)."""
    pass

