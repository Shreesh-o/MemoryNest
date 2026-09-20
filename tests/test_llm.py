"""Tests for LLM service (mock mode)."""

from __future__ import annotations

import os

from app.services import llm_service


def test_mock_mode(monkeypatch):
    monkeypatch.setenv("MOCK_LLM", "1")
    # Reload module to pick up env var? No, generate() checks env each call.
    out = llm_service.generate("test prompt", system="sys")
    assert out == llm_service._MOCK_RESPONSE


def test_mock_mode_without_system(monkeypatch):
    monkeypatch.setenv("MOCK_LLM", "1")
    out = llm_service.generate("test prompt")
    assert out == llm_service._MOCK_RESPONSE


def test_is_ollama_available_cached(monkeypatch):
    # Clear cache
    llm_service._ollama_available_cache = None
    # Mock requests.get
    class MockResp:
        def __init__(self, models):
            self.status_code = 200
            self._models = models
        def json(self):
            return {"models": self._models}

    def mock_get(url, timeout):
        return MockResp([{"name": "qwen2.5:3b-instruct"}])

    monkeypatch.setattr("app.services.llm_service.requests.get", mock_get)
    assert llm_service.is_ollama_available() is True
    assert llm_service._ollama_available_cache is True

    # Second call uses cache
    call_count = 0
    def mock_get2(url, timeout):
        nonlocal call_count
        call_count += 1
        return MockResp([])
    monkeypatch.setattr("app.services.llm_service.requests.get", mock_get2)
    # Should use cache
    assert llm_service.is_ollama_available() is True
    assert call_count == 0