

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
