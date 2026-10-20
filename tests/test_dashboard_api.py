"""Tests for dashboard API endpoints."""

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
    resp = client.post("/api/auth/register", json={"username": "dashuser", "password": "dashpass123"})
    assert resp.status_code == 201, f"Register failed: {resp.text}"

    resp = client.post("/api/auth/login", json={"username": "dashuser", "password": "dashpass123"})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return dict(resp.cookies)


def test_dashboard_empty(client, auth_user):
    """Dashboard returns zeros when user has no data."""
    cookies = auth_user
    resp = client.get("/api/dashboard", cookies=cookies)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_documents"] == 0
    assert data["ready_documents"] == 0
    assert data["failed_documents"] == 0
    assert data["pending_documents"] == 0
    assert data["total_chunks"] == 0
    assert data["pending_events"] == []
    assert data["confirmed_events"] == []
    assert data["upcoming_deadlines"] == []
    assert data["recent_conversations"] == []


def test_dashboard_with_documents(client, auth_user):
    """Dashboard shows document stats after upload."""
    cookies = auth_user

    import os
    os.environ["MOCK_LLM"] = "1"

    # Upload a document
    files = {"files": ("test.txt", b"This is test content for dashboard.", "text/plain")}
    resp = client.post("/api/documents/upload", files=files, cookies=cookies)
    assert resp.status_code == 200, f"Upload failed: {resp.text}"
    doc = resp.json()[0]

    resp = client.get("/api/dashboard", cookies=cookies)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_documents"] == 1
    assert data["ready_documents"] == 1
    assert data["failed_documents"] == 0
    assert data["pending_documents"] == 0
    assert data["total_chunks"] >= 0


def test_dashboard_another_user(client, auth_user):
    """Another user's dashboard shows their own data only."""
    cookies = auth_user

    import os
    os.environ["MOCK_LLM"] = "1"

    # Upload a document as first user
    files = {"files": ("test.txt", b"First user document.", "text/plain")}
    resp = client.post("/api/documents/upload", files=files, cookies=cookies)
    assert resp.status_code == 200

    # Create second user
    resp = client.post("/api/auth/register", json={"username": "otheruser", "password": "otherpass123"})
    assert resp.status_code == 201

    resp = client.post("/api/auth/login", json={"username": "otheruser", "password": "otherpass123"})
    assert resp.status_code == 200
    other_cookies = dict(resp.cookies)

    # Second user's dashboard should be empty
    resp = client.get("/api/dashboard", cookies=other_cookies)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_documents"] == 0
    assert data["ready_documents"] == 0