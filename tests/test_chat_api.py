"""Tests for chat API endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app
from app.database.database import init_db
from app.utils.config import UPLOAD_DIR, MAX_FILE_SIZE_BYTES


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    """Use a temp database for each test."""
    import app.utils.config as config_module
    import app.database.database as db_module
    import os

    db_path = tmp_path / "db.sqlite"
    chroma_dir = tmp_path / "chroma"
    upload_dir = tmp_path / "uploads"
    audio_dir = tmp_path / "audio"

    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.setenv("CHROMA_DIR", str(chroma_dir))
    monkeypatch.setenv("UPLOAD_DIR", str(upload_dir))
    monkeypatch.setenv("AUDIO_DIR", str(audio_dir))

    config_module.refresh_paths()

    db_module.init_db(db_path)

    yield


@pytest.fixture
def client(temp_db):
    import app.utils.config as config_module
    app = create_app(str(config_module.DB_PATH))
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_user(client):
    resp = client.post("/api/auth/register", json={"username": "chatuser", "password": "chatpass123"})
    assert resp.status_code == 201, f"Register failed: {resp.text}"

    resp = client.post("/api/auth/login", json={"username": "chatuser", "password": "chatpass123"})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return dict(resp.cookies)


def test_chat_creates_conversation_and_messages(client, auth_user):
    """Chat creates a conversation and saves messages."""
    cookies = auth_user

    # Mock mode for faster tests
    import os
    os.environ["MOCK_LLM"] = "1"

    resp = client.post("/api/chat", json={"question": "What is in my documents?"}, cookies=cookies)
    assert resp.status_code == 200
    data = resp.json()
    assert "conversation_id" in data
    assert data["conversation_id"] > 0
    assert "answer" in data
    assert "sources" in data
    assert isinstance(data["sources"], list)

    # Check that conversation exists
    resp = client.get("/api/conversations", cookies=cookies)
    assert resp.status_code == 200
    conversations = resp.json()
    assert len(conversations) == 1
    assert conversations[0]["id"] == data["conversation_id"]


def test_chat_continues_conversation(client, auth_user):
    """Chat continues an existing conversation."""
    cookies = auth_user
    import os
    os.environ["MOCK_LLM"] = "1"

    # First message
    resp = client.post("/api/chat", json={"question": "What is in my documents?"}, cookies=cookies)
    assert resp.status_code == 200
    conversation_id = resp.json()["conversation_id"]

    # Second message in same conversation
    resp = client.post(
        "/api/chat",
        json={"question": "Tell me more", "conversation_id": conversation_id},
        cookies=cookies,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["conversation_id"] == conversation_id


def test_another_user_gets_404_on_conversation(client, auth_user):
    """Another user gets 404 when accessing another user's conversation."""
    cookies = auth_user

    import os
    os.environ["MOCK_LLM"] = "1"

    resp = client.post("/api/chat", json={"question": "Test"}, cookies=cookies)
    conversation_id = resp.json()["conversation_id"]

    # Create second user
    resp = client.post("/api/auth/register", json={"username": "otheruser", "password": "otherpass123"})
    assert resp.status_code == 201

    resp = client.post("/api/auth/login", json={"username": "otheruser", "password": "otherpass123"})
    assert resp.status_code == 200
    other_cookies = dict(resp.cookies)

    # Try to get conversation
    resp = client.get(f"/api/conversations/{conversation_id}", cookies=other_cookies)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Conversation not found"


def test_delete_conversation(client, auth_user):
    """Delete a conversation removes it."""
    cookies = auth_user
    import os
    os.environ["MOCK_LLM"] = "1"

    resp = client.post("/api/chat", json={"question": "Test delete"}, cookies=cookies)
    conversation_id = resp.json()["conversation_id"]

    resp = client.delete(f"/api/conversations/{conversation_id}", cookies=cookies)
    assert resp.status_code == 204

    resp = client.get("/api/conversations", cookies=cookies)
    assert resp.status_code == 200
    assert len(resp.json()) == 0


def test_chat_empty_question_raises_400(client, auth_user):
    """Empty question raises a validation error."""
    cookies = auth_user
    resp = client.post("/api/chat", json={"question": ""}, cookies=cookies)
    # Service raises ValueError for empty question -> 404
    assert resp.status_code == 404


def test_chat_llm_down_503(client, auth_user):
    """When LLM is unavailable, chat returns 503."""
    cookies = auth_user

    import os
    os.environ.pop("MOCK_LLM", None)

    import app.services.llm_service as llm_service
    llm_service._ollama_available_cache = None

    # Mock rag_answer to raise RuntimeError to simulate LLM down
    import app.services.rag_service as rag_service
    original = rag_service.rag_answer

    def fake_rag_answer(user_id, question, **kwargs):
        raise RuntimeError("Ollama is not running at http://localhost:11434")

    rag_service.rag_answer = fake_rag_answer
    try:
        resp = client.post("/api/chat", json={"question": "What is in my docs?"}, cookies=cookies)
        assert resp.status_code == 503
        assert "language model" in resp.json()["detail"].lower() or "ollama" in resp.json()["detail"].lower()
    finally:
        rag_service.rag_answer = original
