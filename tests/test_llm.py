

from __future__ import annotations

import os

from app.services import llm_service


def test_mock_mode(monkeypatch):
    monkeypatch.setenv("MOCK_LLM", "1")
    out = llm_service.generate("test prompt", system="sys")
    assert out == llm_service._MOCK_RESPONSE


def test_mock_mode_without_system(monkeypatch):
    monkeypatch.setenv("MOCK_LLM", "1")
    out = llm_service.generate("test prompt")
    assert out == llm_service._MOCK_RESPONSE


def test_is_mock_mode_env_var_set(monkeypatch):
    monkeypatch.setenv("MOCK_LLM", "1")
    assert llm_service.is_mock_mode() is True


def test_is_mock_mode_env_var_unset(monkeypatch):
    monkeypatch.delenv("MOCK_LLM", raising=False)
    assert llm_service.is_mock_mode() is False


def test_ollama_unavailable_raises(monkeypatch):
    """Ollama unavailable and MOCK_LLM not set -> clear RuntimeError, no fake answer."""
    old_mllm = os.environ.pop("MOCK_LLM", None)
    try:
        llm_service._ollama_available_cache = None
        import app.services.llm_service as ls
        ls._ollama_available_cache = None
        monkeypatch.setattr(ls, "is_ollama_available", lambda: False)
        try:
            llm_service.generate("test prompt")
            assert False, "Expected RuntimeError"
        except RuntimeError as e:
            assert "Ollama is not running" in str(e)
    finally:
        if old_mllm is not None:
            os.environ["MOCK_LLM"] = old_mllm


def test_ollama_availability_ttl_recovery_and_expiration():
    """Verify negative and positive TTL expiration using a controllable clock and mocked requests."""
    from unittest.mock import MagicMock, patch

    current_time = 1000.0

    def mock_clock():
        return current_time

    llm_service.reset_availability_cache()

    # Phase 1: Ollama is down (negative response)
    with patch("requests.get", side_effect=Exception("Connection refused")) as mock_get:
        assert llm_service.is_ollama_available(clock=mock_clock) is False
        assert mock_get.call_count == 1

        # Within negative TTL (e.g. +2s), does not hit network again
        current_time += 2.0
        assert llm_service.is_ollama_available(clock=mock_clock) is False
        assert mock_get.call_count == 1

    # Phase 2: Ollama starts up after negative TTL expires (+6s total)
    current_time += 4.0  # now 1006.0 > 1000.0 + 5.0 (NEGATIVE_TTL)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"models": [{"name": "qwen2.5:3b-instruct:latest"}]}

    with patch("requests.get", return_value=mock_resp) as mock_get:
        assert llm_service.is_ollama_available(clock=mock_clock) is True
        assert mock_get.call_count == 1

        # Within positive TTL (+10s), returns cached True without network call
        current_time += 10.0
        assert llm_service.is_ollama_available(clock=mock_clock) is True
        assert mock_get.call_count == 1

    # Phase 3: Ollama goes down after positive TTL expires (+35s)
    current_time += 25.0  # now 1041.0 > 1006.0 + 30.0 (POSITIVE_TTL)
    with patch("requests.get", side_effect=Exception("Connection reset")) as mock_get:
        assert llm_service.is_ollama_available(clock=mock_clock) is False
        assert mock_get.call_count == 1

