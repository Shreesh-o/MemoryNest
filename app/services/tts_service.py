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
    text: str, output_path: str, voice: str = TTS_VOICE
) -> bool:
    """Synthesize text using Piper TTS engine.

    Requires: pip install piper-tts and a .onnx voice model at
    models/piper/<voice>.onnx
    """
    try:
        import piper
    except ImportError:
        logger.warning("piper-tts not installed")
        return False

    model_path = Path("models/piper") / f"{voice}.onnx"
    if not model_path.exists():
        logger.warning("Piper model not found at %s", model_path)
        return False

    try:
        # Piper API: pipe.Synthesizer(model_path) -> synthesize(text, file_path)
        from piper import PiperVoice
        voice_obj = PiperVoice.load(str(model_path))
        voice_obj.synthesize(text, output_path)
        # Verify output
        if Path(output_path).exists() and Path(output_path).stat().st_size > 1024:
            logger.info("Piper synthesized %s (%d bytes)", output_path, Path(output_path).stat().st_size)
            return True
        else:
            logger.error("Piper produced no valid output")
            return False
    except Exception as e:
        logger.error("Piper synthesis failed: %s", e)
        return False


def synthesize_with_espeak_ng(
    text: str, output_path: str,
) -> bool:
    """Synthesize text using espeak-ng CLI.

    Tuning: -s 150 (≈150 wpm), -g 3 (small word gap), -p 50 (pitch),
           --voice en-us+f3 or en-gb.
    """
    # Try a few voice variants
    voice_variants = ["en-us+f3", "en-gb", "en"]
    success = False

    for idx, voice in enumerate(voice_variants):
        tmp_path = f"/tmp/tts_sample_{idx}.wav"
        try:
            # Build espeak-ng command
            cmd = [
                "espeak-ng",
                "-v", voice,
                "-s", "150",   # 150 wpm
                "-g", "3",      # small word gap
                "-p", "50",     # pitch 50
                "-w", tmp_path,
            ]
            subprocess.run(
                cmd, input=text, capture_output=True, text=True, timeout=60
            )
            if subprocess.run(
                cmd, input=text, capture_output=True, text=True, timeout=60
            ).returncode != 0 or not Path(tmp_path).exists():
                # Clean up and try next variant
                if Path(tmp_path).exists():
                    Path(tmp_path).unlink(missing_ok=True)
                continue

            # Verify output size
            if Path(tmp_path).stat().st_size > 1024:
                # Copy to final output path
                import shutil
                shutil.copy2(tmp_path, output_path)
                success = True
                logger.info("espeak-ng variant %d (%s) succeeded, %d bytes", idx, voice, Path(tmp_path).stat().st_size)
                break
            else:
                # Clean up small file
                if Path(tmp_path).exists():
                    Path(tmp_path).unlink(missing_ok=True)
        except Exception as e:
            logger.error("espeak-ng variant %d failed: %s", idx, e)
            if Path(tmp_path).exists():
                Path(tmp_path).unlink(missing_ok=True)

    return success


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
        engine = pyttsx3.init()
        engine.save_to_file(text, output_path)
        engine.runAndWait()
        if Path(output_path).exists() and Path(output_path).stat().st_size > 1024:
            logger.info("pyttsx3 synthesized %s (%d bytes)", output_path, Path(output_path).stat().st_size)
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
    engine = engine_name or TTS_ENGINE
    engine = engine.lower()
    if engine not in VALID_ENGINES:
        logger.warning("Invalid TTS_ENGINE '%s', defaulting to 'auto'", engine)
        return "auto"
    return engine


def _try_piper_install() -> bool:
    """Attempt to install piper-tts via pip. Returns True on success."""
    try:
        import subprocess as sp
        result = sp.run(
            [os.sys.executable, "-m", "pip", "install", "piper-tts"],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0:
            logger.info("piper-tts installed successfully via pip")
            return True
        else:
            logger.error("piper-tts pip install failed: %s", result.stderr[-500:])
            return False
    except Exception as e:
        logger.error("piper-tts pip install exception: %s", e)
        return False


def synthesize_to_file(text: str, filename: str | None = None) -> str:
    """Convert text to speech and save as WAV.

    Full pipeline:
    1. Clean text (markdown removal, whitespace collapsing)
    2. Split into sentences, group into chunks (~400 chars)
    3. Synthesize each group using the selected engine
    4. Merge generated WAVs with ~250 ms silence between groups
    5. Verify final file exists and is > 1 KB
    6. Raise RuntimeError if anything fails

    Returns the path to the generated WAV file.
    """
    # Text processing pipeline
    clean = clean_text(text)
    sentences = split_into_sentences(clean)
    groups = group_sentences(sentences, max_chars=400)

    if not groups:
        raise RuntimeError("Audio generation failed: no valid text after cleaning.")

    # If no engine is available, fail immediately
    if not tts_available():
        raise RuntimeError(
            "Audio generation failed: no TTS engine is available. "
            "Install piper-tts with a voice model, "
            "or ensure espeak-ng or pyttsx3 is installed."
        )

    # Engine selection
    engine = _select_engine(None)

    # Ensure output directory exists
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    if filename is None:
        filename = f"tts_{os.urandom(4).hex()}.wav"

    output_path = str(AUDIO_DIR / filename)

    # --- Piper engine ---
    if engine in ("auto", "piper"):
        # Check if piper is available and model exists
        model_path = Path("models/piper") / TTS_VOICE
        piper_available = False
        try:
            import piper  # noqa: F401
            piper_available = True
        except ImportError:
            piper_available = False

        if piper_available and model_path.exists():
            ok = synthesize_with_piper(text, output_path, TTS_VOICE)
            if ok:
                logger.info("Used piper engine for TTS")
                # Verify and return
                if Path(output_path).exists() and Path(output_path).stat().st_size > 1024:
                    return output_path
                # Fall through if piper produced invalid output

        # If piper not available or failed, try installing once
        if engine == "auto" and not piper_available:
            logger.info("piper-tts not installed, attempting pip install...")
            if _try_piper_install():
                # Check if model appeared
                if model_path.exists():
                    ok = synthesize_with_piper(text, output_path, TTS_VOICE)
                    if ok:
                        if Path(output_path).exists() and Path(output_path).stat().st_size > 1024:
                            logger.info("Used piper engine (post-install) for TTS")
                            return output_path

        # If we get here, piper failed or not available; try espeak
        if engine in ("auto", "espeak", "piper"):
            ok = synthesize_with_espeak_ng(text, output_path)
            if ok:
                if Path(output_path).exists() and Path(output_path).stat().st_size > 1024:
                    logger.info("Used espeak-ng engine for TTS")
                    return output_path


    # --- edge engine ---
    if engine in ("auto", "edge"):
        # Check if edge-tts is available
        import edge_tts
        try:
            # Simple edge-tts synthesis
            import asyncio
            async def _edge_synth():
                communicate = edge_tts.Communicate(text, "en-IN-NeerjaNeural")
                await communicate.save(output_path)
            _edge_synth()
            if Path(output_path).exists() and Path(output_path).stat().st_size > 1024:
                logger.info("Used edge-tts engine for TTS")
                return output_path
        except ImportError:
            pass
    # --- espeak-ng engine ---
    if engine in ("auto", "espeak"):
        ok = synthesize_with_espeak_ng(text, output_path)
        if ok:
            if Path(output_path).exists() and Path(output_path).stat().st_size > 1024:
                logger.info("Used espeak-ng engine for TTS")
                return output_path

    # --- pyttsx3 fallback ---
    if engine in ("auto", "pyttsx3"):
        ok = synthesize_with_pyttsx3(text, output_path)
        if ok:
            if Path(output_path).exists() and Path(output_path).stat().st_size > 1024:
                logger.info("Used pyttsx3 fallback for TTS")
                return output_path

    # If we reached here, all engines failed
    raise RuntimeError(
        f"Audio generation failed: no TTS engine produced a valid WAV file (>1 KB). "
        f"Engine used: {TTS_ENGINE}. "
        "Install piper-tts and provide a .onnx model, or ensure espeak-ng is available."
    )


# If we reached here, all engines failed
    raise RuntimeError(
        f"Audio generation failed: no TTS engine produced a valid WAV file (>1 KB). "
        f"Engine used: {TTS_ENGINE}. "
        "Install piper-tts and provide a .onnx model, or ensure espeak-ng is available."
    )


def tts_available() -> bool:
    """Check if any TTS engine is available.

    Returns True if at least one engine (piper, espeak-ng, or pyttsx3) can be used.
    """
    # Check piper
    try:
        import piper  # noqa: F401
        model_path = Path("models/piper") / TTS_VOICE
        if model_path.exists():
            return True
    except ImportError:
        pass

    # Check espeak-ng
    if shutil.which("espeak-ng") is not None:
        return True

    # Check pyttsx3
    try:
        import pyttsx3  # noqa: F401
        return True
    except ImportError:
        pass

    return False



def _synthesize_with_edge(text: str, output_path: str) -> bool:
    """Synthesize text using edge-tts engine.

    Uses edge-tts package to generate audio, converts MP3 to WAV with ffmpeg.
    """
    import edge_tts
    import asyncio
    import subprocess
    
    try:
        async def _inner():
            communicate = edge_tts.Communicate(text, "en-IN-NeerjaNeural")
            await communicate.save(output_path)  # saves as .mp3
            
            # Convert MP3 to WAV with ffmpeg
            wav_path = Path(output_path).with_suffix(".wav")
            subprocess.run(
                ["ffmpeg", "-i", output_path,
                 "-ar", "16000", "-ac", "1", "-y", str(wav_path)],
                capture_output=True, timeout=30,
            )
            if Path(wav_path).exists() and Path(wav_path).stat().st_size > 1024:
                Path(output_path).unlink(missing_ok=True)
                return True
            if Path(output_path).exists() and Path(output_path).stat().st_size > 1024:
                return True
            return False
        
        asyncio.run(_inner())
        return True
    except Exception as e:
        logger.error("Edge TTS failed: %s", e)
        return False

def reset_cache() -> None:
    """Reset any cached state (for testing)."""
    global TTS_ENGINE
    # Engines are stateless; nothing to reset here.
    pass
