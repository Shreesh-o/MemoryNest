"""Tests for reminders cancellation and email status API endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app
from app.database.database import init_db


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    """Use a temp database for each test."""
    import app.utils.config as config_module
    import app.database.database as db_module

    db_path = tmp_path / "db.sqlite"
    chroma_dir = tmp_path / "chroma"
    upload_dir = tmp_path / "uploads"
    audio_dir = tmp_path / "audio"

    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.setenv("CHROMA_DIR", str(chroma_dir))
    monkeypatch.setenv("UPLOAD_DIR", str(upload_dir))
    monkeypatch.setenv("AUDIO_DIR", str(audio_dir))

    config_module.refresh_paths()

    orig_db_path = config_module.DB_PATH
    orig_chroma_dir = config_module.CHROMA_DIR
    orig_upload_dir = config_module.UPLOAD_DIR
    orig_audio_dir = config_module.AUDIO_DIR

    db_module.init_db(db_path)

    yield

    config_module.DB_PATH = orig_db_path
    config_module.CHROMA_DIR = orig_chroma_dir
    config_module.UPLOAD_DIR = orig_upload_dir
    config_module.AUDIO_DIR = orig_audio_dir


@pytest.fixture
def client(temp_db):
    """Create a TestClient with lifespan for each test."""
    import app.utils.config as config_module
    db_path = str(config_module.DB_PATH)
    app = create_app(db_path)
    with TestClient(app) as test_client:
        yield test_client


def _register_and_login(client: TestClient, username: str, password: str) -> dict:
    """Register and login a user, return cookies dict."""
    resp = client.post("/api/auth/register", json={"username": username, "password": password})
    assert resp.status_code == 201, f"Register failed: {resp.text}"

    resp = client.post("/api/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.text}"

    return dict(resp.cookies)


def _upload_document(client: TestClient, cookies: dict, filename: str, content: bytes) -> int:
    """Upload a document and return doc_id."""
    files = {"files": (filename, content, "text/plain")}
    resp = client.post("/api/documents/upload", files=files, cookies=cookies)
    assert resp.status_code == 200, f"Upload failed: {resp.text}"
    return resp.json()[0]["doc_id"]


def _extract_events(client: TestClient, cookies: dict, doc_id: int) -> list:
    """Extract events from document and return list of events."""
    resp = client.post(f"/api/documents/{doc_id}/extract-events", cookies=cookies)
    assert resp.status_code == 201, f"Extract failed: {resp.text}"
    return resp.json()["events"]


def _confirm_event(client: TestClient, cookies: dict, event_id: int, remind_at: str | None = None) -> dict:
    """Confirm an event and return the event."""
    payload = {"remind_at": remind_at} if remind_at else {}
    resp = client.post(f"/api/events/{event_id}/confirm", json=payload, cookies=cookies)
    assert resp.status_code == 200, f"Confirm failed: {resp.text}"
    return resp.json()


def test_cancel_removes_reminder_and_reverts_event_to_pending(client):
    """Cancel removes the reminder and returns the event to pending."""
    cookies = _register_and_login(client, "testuser1", "testpass123")
    doc_id = _upload_document(client, cookies, "notice.txt", b"Flight on 2026-11-20 at 14:00")
    events = _extract_events(client, cookies, doc_id)
    event_id = events[0]["id"]

    _confirm_event(client, cookies, event_id)

    # Check reminder exists and event is confirmed
    reminders = client.get("/api/reminders", cookies=cookies).json()
    assert len(reminders) == 1
    reminder_id = reminders[0]["id"]
    assert reminders[0]["status"] == "scheduled"

    events_list = client.get("/api/events", cookies=cookies).json()
    ev = next(e for e in events_list if e["id"] == event_id)
    assert ev["status"] == "confirmed"

    # Cancel reminder
    del_resp = client.delete(f"/api/reminders/{reminder_id}", cookies=cookies)
    assert del_resp.status_code == 204

    # Reminder is removed
    reminders_after = client.get("/api/reminders", cookies=cookies).json()
    assert len(reminders_after) == 0

    # Event status is reverted to pending
    events_after = client.get("/api/events", cookies=cookies).json()
    ev_after = next(e for e in events_after if e["id"] == event_id)
    assert ev_after["status"] == "pending"

    # User can confirm it again
    _confirm_event(client, cookies, event_id)
    reminders_reconfirmed = client.get("/api/reminders", cookies=cookies).json()
    assert len(reminders_reconfirmed) == 1


def test_another_user_gets_404_on_cancel(client):
    """Another user gets 404 when cancelling a reminder they do not own."""
    cookies1 = _register_and_login(client, "owner_user", "pass123")
    doc_id = _upload_document(client, cookies1, "doc1.txt", b"Meeting on 2026-12-01")
    events = _extract_events(client, cookies1, doc_id)
    _confirm_event(client, cookies1, events[0]["id"])
    reminders1 = client.get("/api/reminders", cookies=cookies1).json()
    reminder_id = reminders1[0]["id"]

    cookies2 = _register_and_login(client, "attacker_user", "pass123")
    resp = client.delete(f"/api/reminders/{reminder_id}", cookies=cookies2)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Reminder not found"

    # Original reminder is still intact
    reminders1_after = client.get("/api/reminders", cookies=cookies1).json()
    assert len(reminders1_after) == 1


def test_cancel_unknown_id_gets_404(client):
    """Cancelling a non-existent reminder returns 404."""
    cookies = _register_and_login(client, "user_unknown", "pass123")
    resp = client.delete("/api/reminders/999999", cookies=cookies)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Reminder not found"


def test_check_with_email_unconfigured_returns_configured_false_and_leaves_scheduled(client, monkeypatch):
    """Check with email unconfigured returns configured=false and leaves reminders scheduled."""
    import app.utils.config as cfg
    monkeypatch.setenv("EMAIL_USERNAME", "")
    monkeypatch.setenv("EMAIL_APP_PASSWORD", "")
    monkeypatch.setattr(cfg, "EMAIL_USERNAME", "")
    monkeypatch.setattr(cfg, "EMAIL_APP_PASSWORD", "")

    cookies = _register_and_login(client, "user_due", "pass123")
    doc_id = _upload_document(client, cookies, "test.txt", b"Meeting on 2026-12-25")
    events = _extract_events(client, cookies, doc_id)
    event_id = events[0]["id"]

    # Confirm with past remind_at so it is due
    _confirm_event(client, cookies, event_id, remind_at="2020-01-01 09:00:00")

    # Call /api/reminders/check
    resp = client.post("/api/reminders/check", cookies=cookies)
    assert resp.status_code == 200
    data = resp.json()

    assert data["configured"] is False
    assert data["sent"] == 0
    assert data["failed"] == 0
    assert data["skipped"] == 1
    assert "Email is not set up. Add EMAIL_USERNAME and EMAIL_APP_PASSWORD to the .env file." in data["errors"]

    # Verify reminder is still scheduled, NOT marked failed
    reminders = client.get("/api/reminders", cookies=cookies).json()
    assert len(reminders) == 1
    assert reminders[0]["status"] == "scheduled"


def test_health_has_email_configured(client, monkeypatch):
    """GET /api/health includes email_configured: bool."""
    import app.utils.config as cfg

    # When unconfigured
    monkeypatch.setenv("EMAIL_USERNAME", "")
    monkeypatch.setenv("EMAIL_APP_PASSWORD", "")
    monkeypatch.setattr(cfg, "EMAIL_USERNAME", "")
    monkeypatch.setattr(cfg, "EMAIL_APP_PASSWORD", "")

    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "email_configured" in data
    assert data["email_configured"] is False

    # When configured
    monkeypatch.setenv("EMAIL_USERNAME", "me@example.com")
    monkeypatch.setenv("EMAIL_APP_PASSWORD", "secret123")
    monkeypatch.setattr(cfg, "EMAIL_USERNAME", "me@example.com")
    monkeypatch.setattr(cfg, "EMAIL_APP_PASSWORD", "secret123")

    resp2 = client.get("/api/health")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["email_configured"] is True
