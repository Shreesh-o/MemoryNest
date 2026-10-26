"""Ollama LLM client with mock fallback for testing."""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Optional

import requests

from app.utils.config import OLLAMA_HOST, OLLAMA_MODEL

_MOCK_RESPONSE = (
    "This is a mock LLM response. In a real deployment, "
    "Ollama would generate an answer based on the provided context."
)

_cache_lock = threading.Lock()
_cache_status: Optional[bool] = None
_cache_timestamp: float = 0.0
_ollama_available_cache: Optional[bool] = None

POSITIVE_TTL: float = 30.0  # seconds to cache positive availability
NEGATIVE_TTL: float = 5.0   # seconds to cache negative availability (allows fast recovery)


def reset_availability_cache() -> None:
    """Clear the cached availability status (thread-safe)."""
    global _cache_status, _cache_timestamp, _ollama_available_cache
    with _cache_lock:
        _cache_status = None
        _cache_timestamp = 0.0
        _ollama_available_cache = None


def is_mock_mode() -> bool:
    """Return True when MOCK_LLM=1 is set, evaluated at call time."""
    return os.environ.get("MOCK_LLM") == "1"


def is_ollama_available(timeout: float = 2.0, clock: Optional[callable] = None) -> bool:
    """Check if Ollama server is reachable and the model is loaded.

    Uses a thread-safe short TTL cache:
    - Positive checks cache for POSITIVE_TTL (30s) to avoid redundant network overhead.
    - Negative checks cache for NEGATIVE_TTL (5s) to enable fast automatic recovery
      when Ollama starts up after the API.
    """
    global _cache_status, _cache_timestamp, _ollama_available_cache
    now = clock() if clock else time.monotonic()

    with _cache_lock:
        if _ollama_available_cache is None:
            _cache_status = None

        if _cache_status is not None:
            ttl = POSITIVE_TTL if _cache_status else NEGATIVE_TTL
            if (now - _cache_timestamp) < ttl:
                return _cache_status

    status = False
    try:
        r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=timeout)
        if r.status_code == 200:
            models = r.json().get("models", [])
            status = any(OLLAMA_MODEL in m.get("name", "") for m in models)
    except Exception:
        status = False

    with _cache_lock:
        _cache_status = status
        _cache_timestamp = now
        _ollama_available_cache = status

    return status


def generate(
    prompt: str,
    system: Optional[str] = None,
    temperature: float = 0.1,
    max_tokens: int = 512,
) -> str:
    """Generate text from Ollama.

    - is_mock_mode() is evaluated at call time; if True, a mock response
      is returned and a warning is logged for the UI sidebar.
    - If Ollama is unavailable and MOCK_LLM is not set, raises RuntimeError.
    - Otherwise performs the real HTTP call.
    """
    if is_mock_mode():
        logging.warning("Mock LLM mode is active: answers are not real.")
        return _MOCK_RESPONSE
    if not is_ollama_available():
        raise RuntimeError(
            f"Ollama is not running at {OLLAMA_HOST}. Start it with: ollama serve"
        )
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }
    if system:
        payload["system"] = system
    try:
        # Model load can take ~7s on CPU; give generous timeout
        r = requests.post(f"{OLLAMA_HOST}/api/generate", json=payload, timeout=180)
        r.raise_for_status()
        data = r.json()
        return data.get("response", "").strip()
    except Exception as e:
        reset_availability_cache()
        raise RuntimeError(f"LLM request failed: {e}") from None