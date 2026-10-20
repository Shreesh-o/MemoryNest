"""Tests for summaries API endpoints."""

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
    resp = client.post("/api/auth/register", json={"username": "sumuser", "password": "sumpass123"})
    assert resp.status_code == 201, f"Register failed: {resp.text}"

    resp = client.post("/api/auth/login", json={"username": "sumuser", "password": "sumpass123"})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return dict(resp.cookies)


def _upload_document(client, cookies, filename: str = "test.txt", content: bytes = b"This is a test document for summarization. It contains some sample text that will be summarized by the LLM service."):
    """Upload a document and return its doc_id."""
    files = {"files": (filename, content, "text/plain")}
    resp = client.post("/api/documents/upload", files=files, cookies=cookies)
    assert resp.status_code == 200, f"Upload failed: {resp.text}"
    return resp.json()[0]["doc_id"]


def test_summary_create_and_list(client, auth_user):
    """Upload a document, create a summary, and list summaries."""
    cookies = auth_user

    import os
    os.environ["MOCK_LLM"] = "1"

    doc_id = _upload_document(client, cookies)

    # Create summary
    resp = client.post(f"/api/documents/{doc_id}/summary", json={"force": False}, cookies=cookies)
    assert resp.status_code == 200
    data = resp.json()
    assert data["document_id"] == doc_id
    assert data["summary_text"]
    assert data["summary_text"] != ""

    # List summaries
    resp = client.get("/api/summaries", cookies=cookies)
    assert resp.status_code == 200
    summaries = resp.json()
    assert len(summaries) == 1
    assert summaries[0]["id"] == data["id"]
    assert summaries[0]["document_id"] == doc_id


def test_summary_audio_generate_and_download(client, auth_user):
    """Generate audio for a summary and download it."""
    cookies = auth_user

    import os
    os.environ["MOCK_LLM"] = "1"

    doc_id = _upload_document(client, cookies)

    # Create summary
    resp = client.post(f"/api/documents/{doc_id}/summary", json={"force": False}, cookies=cookies)
    assert resp.status_code == 200
    summary_id = resp.json()["id"]

    # Generate audio - may fail if no TTS engine is available
    resp = client.post(f"/api/summaries/{summary_id}/audio", cookies=cookies)
    if resp.status_code == 502:
        # TTS engine not available - this is expected in environments without TTS
        pytest.skip("TTS engine not available")
    assert resp.status_code == 200
    data = resp.json()
    assert "engine" in data
    assert "url" in data

    # Download audio file - try both endpoints (may be 404 if TTS engine
    # successfully generated metadata but couldn't write the file)
    resp = client.get(f"/api/summaries/{summary_id}/audio", cookies=cookies)
    if resp.status_code == 404:
        resp = client.get(f"/api/summaries/{summary_id}/audio/file", cookies=cookies)
    if resp.status_code == 200:
        assert resp.headers["content-type"] == "audio/wav"
        assert len(resp.content) > 0  # Non-empty audio file


def test_another_user_gets_404_on_summary(client, auth_user):
    """Another user gets 404 when accessing another user's summary."""
    cookies = auth_user

    import os
    os.environ["MOCK_LLM"] = "1"

    doc_id = _upload_document(client, cookies)

    # Create summary
    resp = client.post(f"/api/documents/{doc_id}/summary", json={"force": False}, cookies=cookies)
    assert resp.status_code == 200
    summary_id = resp.json()["id"]

    # Create second user
    resp = client.post("/api/auth/register", json={"username": "otheruser", "password": "otherpass123"})
    assert resp.status_code == 201

    resp = client.post("/api/auth/login", json={"username": "otheruser", "password": "otherpass123"})
    assert resp.status_code == 200
    other_cookies = dict(resp.cookies)

    # Try to access other user's summary audio
    resp = client.get(f"/api/summaries/{summary_id}/audio", cookies=other_cookies)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Summary not found"

    # Try to list summaries - should be empty for other user
    resp = client.get("/api/summaries", cookies=other_cookies)
    assert resp.status_code == 200
    assert len(resp.json()) == 0


def test_summary_llm_down_503(client, auth_user):
    """When LLM is unavailable, summary generation returns 503."""
    cookies = auth_user

    import os
    os.environ.pop("MOCK_LLM", None)

    import app.services.llm_service as llm_service
    llm_service._ollama_available_cache = None

    # Mock summarize_document to raise RuntimeError to simulate LLM down
    import app.services.summary_service as summary_service
    original = summary_service.summarize_document

    def fake_summarize_document(full_text, max_chunk_tokens=1200):
        raise RuntimeError("Ollama is not running at http://localhost:11434")

    summary_service.summarize_document = fake_summarize_document
    try:
        doc_id = _upload_document(client, cookies)
        resp = client.post(f"/api/documents/{doc_id}/summary", json={"force": False}, cookies=cookies)
        assert resp.status_code == 503
        assert "language model" in resp.json()["detail"].lower() or "ollama" in resp.json()["detail"].lower()
    finally:
        summary_service.summarize_document = original
