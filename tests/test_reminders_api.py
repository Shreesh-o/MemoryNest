"""Tests for reminders API endpoints."""

from __future__ import annotations

import icalendar
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

    db_path = tmp_path / "db.sqlite"
    chroma_dir = tmp_path / "chroma"
    upload_dir = tmp_path / "uploads"
    audio_dir = tmp_path / "audio"

    print(f"DEBUG temp_db: tmp_path={tmp_path}, db_path={db_path}")

    # Set environment variables BEFORE any config access
    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.setenv("CHROMA_DIR", str(chroma_dir))
    monkeypatch.setenv("UPLOAD_DIR", str(upload_dir))
    monkeypatch.setenv("AUDIO_DIR", str(audio_dir))

    # Verify environment variables are set
    import os
    print(f"DEBUG temp_db: os.environ[DB_PATH]={os.environ.get('DB_PATH')}")

    # Refresh config paths from environment variables
    config_module.refresh_paths()

    print(f"DEBUG temp_db: DB_PATH after refresh={config_module.DB_PATH}")
    print(f"DEBUG temp_db: get_db_path()={config_module.get_db_path()}")

    # Store original values (after refresh, these are the temp paths)
    orig_db_path = config_module.DB_PATH
    orig_chroma_dir = config_module.CHROMA_DIR
    orig_upload_dir = config_module.UPLOAD_DIR
    orig_audio_dir = config_module.AUDIO_DIR

    print(f"DEBUG temp_db: DB_PATH after refresh={config_module.DB_PATH}")

    # Re-init DB with explicit path
    db_module.init_db(db_path)

    yield

    # Cleanup - restore original values (not really needed since monkeypatch handles env vars)
    config_module.DB_PATH = orig_db_path
    config_module.CHROMA_DIR = orig_chroma_dir
    config_module.UPLOAD_DIR = orig_upload_dir
    config_module.AUDIO_DIR = orig_audio_dir
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

    # Return cookies as dict for use in subsequent requests
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
    events = resp.json()["events"]
    print(f"DEBUG _extract_events: {events}")
    return events


def _confirm_event(client: TestClient, cookies: dict, event_id: int, remind_at: str | None = None) -> dict:
    """Confirm an event and return the event."""
    payload = {"remind_at": remind_at} if remind_at else {}
    resp = client.post(f"/api/events/{event_id}/confirm", json=payload, cookies=cookies)
    assert resp.status_code == 200, f"Confirm failed: {resp.text}"
    return resp.json()


def test_extract_events_from_document(client):
    """Upload a TXT with a future date -> events appear."""
    cookies = _register_and_login(client, "testuser", "testpass123")

    doc_id = _upload_document(client, cookies, "test.txt", b"Meeting on 2026-12-25 at 10:00")

    events = _extract_events(client, cookies, doc_id)
    assert len(events) >= 1

    event = events[0]
    assert event["event_text"] == "Meeting on 2026-12-25 at 10:00"
    assert event["event_date"] == "2026-12-25"
    assert event["raw_date"] == "2026-12-25"
    assert event["status"] == "pending"


def test_confirm_event_creates_reminder(client):
    """Confirm an event -> creates a reminder."""
    cookies = _register_and_login(client, "testuser2", "testpass123")

    doc_id = _upload_document(client, cookies, "test.txt", b"Meeting on 2026-12-25")
    events = _extract_events(client, cookies, doc_id)
    event_id = events[0]["id"]

    event = _confirm_event(client, cookies, event_id)
    assert event["status"] == "confirmed"

    # Check reminder was created
    resp = client.get("/api/reminders", cookies=cookies)
    assert resp.status_code == 200
    reminders = resp.json()
    assert len(reminders) == 1
    assert reminders[0]["event_id"] == event_id
    assert reminders[0]["status"] == "scheduled"
    assert "2026-12-25 09:00:00" in reminders[0]["remind_at"]


def test_ics_parses_with_kolkata_timezone(client):
    """The .ics parses back with icalendar and start date is in Asia/Kolkata."""
    cookies = _register_and_login(client, "testuser3", "testpass123")

    doc_id = _upload_document(client, cookies, "test.txt", b"Meeting on 2026-12-25")
    events = _extract_events(client, cookies, doc_id)
    event_id = events[0]["id"]

    _confirm_event(client, cookies, event_id)

    # Get .ics
    resp = client.get("/api/calendar.ics", cookies=cookies)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "text/calendar; charset=utf-8"
    assert "attachment" in resp.headers["content-disposition"]

    # Parse with icalendar
    ics_bytes = resp.content
    cal = icalendar.Calendar.from_ical(ics_bytes)

    for component in cal.walk():
        if component.name == "VEVENT":
            dtstart = component.get("dtstart")
            assert dtstart is not None
            assert hasattr(dtstart, "dt")
            assert dtstart.dt.tzinfo is not None
            assert str(dtstart.dt.tzinfo) == "Asia/Kolkata"


def test_another_user_gets_404(client):
    """Another user gets 404 when accessing events they don't own."""
    cookies1 = _register_and_login(client, "user1", "pass123")

    doc_id = _upload_document(client, cookies1, "test.txt", b"Meeting on 2026-12-25")
    events = _extract_events(client, cookies1, doc_id)
    event_id = events[0]["id"]

    # Create second user
    cookies2 = _register_and_login(client, "otheruser", "otherpass123")

    # Try to confirm first user's event
    resp = client.post(f"/api/events/{event_id}/confirm", json={}, cookies=cookies2)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Event not found"

    # Try to list events - should be empty for second user
    resp = client.get("/api/events", cookies=cookies2)
    assert resp.status_code == 200
    assert resp.json() == []

    # Try to get .ics - should be empty for second user
    resp = client.get("/api/calendar.ics", cookies=cookies2)
    assert resp.status_code == 200
    cal = icalendar.Calendar.from_ical(resp.content)
    events = [c for c in cal.walk() if c.name == "VEVENT"]
    assert len(events) == 0


def test_discard_event(client):
    """Discard an event removes it."""
    cookies = _register_and_login(client, "testuser3", "testpass123")

    doc_id = _upload_document(client, cookies, "test.txt", b"Meeting on 2026-12-25")
    events = _extract_events(client, cookies, doc_id)
    event_id = events[0]["id"]

    # Discard event
    resp = client.post(f"/api/events/{event_id}/discard", cookies=cookies)
    assert resp.status_code == 204

    # Event should be gone
    resp = client.get("/api/events", cookies=cookies)
    assert resp.status_code == 200
    assert resp.json() == []


def test_filter_events_by_status(client):
    """List events with status filter."""
    cookies = _register_and_login(client, "testuser4", "testpass123")

    doc_id = _upload_document(client, cookies, "test.txt", b"Meeting on 2026-12-25")
    events = _extract_events(client, cookies, doc_id)
    event_id = events[0]["id"]

    # Filter pending
    resp = client.get("/api/events?status=pending", cookies=cookies)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # Filter confirmed (none yet)
    resp = client.get("/api/events?status=confirmed", cookies=cookies)
    assert resp.status_code == 200
    assert resp.json() == []

    # Confirm event
    _confirm_event(client, cookies, event_id)

    # Filter confirmed
    resp = client.get("/api/events?status=confirmed", cookies=cookies)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # Filter pending (none now)
    resp = client.get("/api/events?status=pending", cookies=cookies)
    assert resp.status_code == 200
    assert resp.json() == []


def test_check_reminders_no_due(client):
    """Check reminders when none are due."""
    cookies = _register_and_login(client, "testuser5", "testpass123")

    resp = client.post("/api/reminders/check", cookies=cookies)
    assert resp.status_code == 200
    data = resp.json()
    assert data["sent"] == 0
    assert data["failed"] == 0
    assert data["details"] == []


def test_ics_with_specific_event_ids(client):
    """Export .ics with specific event IDs."""
    cookies = _register_and_login(client, "testuser6", "testpass123")

    doc_id = _upload_document(client, cookies, "test.txt", b"Meeting on 2026-12-25")
    events = _extract_events(client, cookies, doc_id)
    assert len(events) >= 1

    # Confirm one event
    _confirm_event(client, cookies, events[0]["id"])

    # Export with specific event ID
    resp = client.get(f"/api/calendar.ics?event_ids={events[0]['id']}", cookies=cookies)
    assert resp.status_code == 200

    cal = icalendar.Calendar.from_ical(resp.content)
    vevents = [c for c in cal.walk() if c.name == "VEVENT"]
    assert len(vevents) == 1