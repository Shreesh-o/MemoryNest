"""Tests for semantic search API endpoints."""

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
    resp = client.post("/api/auth/register", json={"username": "searchuser", "password": "searchpass123"})
    assert resp.status_code == 201, f"Register failed: {resp.text}"

    resp = client.post("/api/auth/login", json={"username": "searchuser", "password": "searchpass123"})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return dict(resp.cookies)


def _upload_document(client, cookies, filename="test.txt", content=b"This is a test document for semantic search."):
    """Upload a document and return its doc_id."""
    files = {"files": (filename, content, "text/plain")}
    resp = client.post("/api/documents/upload", files=files, cookies=cookies)
    assert resp.status_code == 200, f"Upload failed: {resp.text}"
    return resp.json()[0]["doc_id"]


def test_search_finds_document(client, auth_user):
    """Upload a TXT with a searchable phrase, then search for it -> hit has right filename."""
    cookies = auth_user

    doc_id = _upload_document(
        client,
        cookies,
        "meeting_notes.txt",
        b"The quarterly budget review meeting is scheduled for March 15, 2026 at 2pm in the conference room.",
    )

    # Search for a phrase from the document
    resp = client.post("/api/search", json={"query": "quarterly budget review meeting"}, cookies=cookies)
    assert resp.status_code == 200, f"Search failed: {resp.text}"
    data = resp.json()
    assert data["query"] == "quarterly budget review meeting"
    assert len(data["hits"]) >= 1
    assert data["hits"][0]["filename"] == "meeting_notes.txt"
    assert data["hits"][0]["document_id"] == doc_id
    assert data["hits"][0]["similarity"] > 0


def test_search_another_user_isolated(client, auth_user):
    """Another user's search returns nothing from the first user's documents."""
    cookies = auth_user

    _upload_document(client, cookies, "secret.txt", b"Confidential salary information for employee John Doe.")

    # Create second user
    resp = client.post("/api/auth/register", json={"username": "otheruser", "password": "otherpass123"})
    assert resp.status_code == 201, f"Register failed: {resp.text}"

    resp = client.post("/api/auth/login", json={"username": "otheruser", "password": "otherpass123"})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    other_cookies = dict(resp.cookies)

    # Other user searches - should find nothing
    resp = client.post("/api/search", json={"query": "salary"}, cookies=other_cookies)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["hits"]) == 0


def test_search_empty_query_400(client, auth_user):
    """Empty query -> 400 (Pydantic validation returns 422)."""
    cookies = auth_user

    resp = client.post("/api/search", json={"query": ""}, cookies=cookies)
    assert resp.status_code in (400, 422)

    resp = client.post("/api/search", json={"query": "   "}, cookies=cookies)
    assert resp.status_code in (400, 422)
