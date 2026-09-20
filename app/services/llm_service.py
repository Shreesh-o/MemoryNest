"""Ollama LLM client with mock fallback for testing."""

from __future__ import annotations

import os
import time
from typing import Optional

import requests

from app.utils.config import OLLAMA_HOST, OLLAMA_MODEL

_MOCK_RESPONSE = (
    "This is a mock LLM response. In a real deployment, "
    "Ollama would generate an answer based on the provided context."
)

_ollama_available_cache: Optional[bool] = None


def is_ollama_available(timeout: float = 2.0) -> bool:
    """Check if Ollama server is reachable and the model is loaded."""
    global _ollama_available_cache
    if _ollama_available_cache is not None:
        return _ollama_available_cache
    try:
        r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=timeout)
        if r.status_code == 200:
            models = r.json().get("models", [])
            _ollama_available_cache = any(OLLAMA_MODEL in m.get("name", "") for m in models)
            return _ollama_available_cache
    except Exception:
        pass
    _ollama_available_cache = False
    return False


def generate(
    prompt: str,
    system: Optional[str] = None,
    temperature: float = 0.1,
    max_tokens: int = 512,
) -> str:
    """Generate text from Ollama. Falls back to mock if unavailable or MOCK_LLM=1."""
    if os.environ.get("MOCK_LLM") == "1" or not is_ollama_available():
        return _MOCK_RESPONSE

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
        return f"[LLM error: {e}]"