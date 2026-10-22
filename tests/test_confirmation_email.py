"""Tests for reminder confirmation email and user-recipient routing."""

from __future__ import annotations

import smtplib
from fastapi.testclient import TestClient
import pytest

from app.api.main import create_app
from app.database.repositories import NotificationLogRepository, ReminderRepository
from app.services import email_service


@pytest.fixture()
def client(tmp_path):
    import app.utils.config as config_module
    db_path = str(config_module.DB_PATH)
    app = create_app(db_path)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def mock_smtp(monkeypatch):
    sent_messages = []

    class MockSMTP:
        def __init__(self, host, port, timeout=30):
            self.host = host
            self.port = port
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

        def starttls(self):
            pass

        def login(self, user, password):
            pass

        def send_message(self, msg):
            sent_messages.append(msg)

    MockSMTP.sent_messages = sent_messages
    monkeypatch.setattr(smtplib, "SMTP", MockSMTP)
    return MockSMTP


def _register_and_login(client: TestClient, username: str, password: str, email: str | None = None) -> dict:
    payload = {"username": username, "password": password}
    if email:
        payload["email"] = email
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 201, f"Register failed: {resp.text}"
    resp = client.post("/api/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return dict(resp.cookies)


def _upload_and_extract(client: TestClient, cookies: dict, filename: str, content: bytes) -> int:
    files = {"files": (filename, content, "text/plain")}
    resp = client.post("/api/documents/upload", files=files, cookies=cookies)
    assert resp.status_code == 200
    doc_id = resp.json()[0]["doc_id"]
    resp = client.post(f"/api/documents/{doc_id}/extract-events", cookies=cookies)
    assert resp.status_code == 201
    return resp.json()["events"][0]["id"]


def test_confirm_email_status_sent_and_recipient(client, mock_smtp, monkeypatch):
    """User with email receives confirmation email at their address, not global fallback."""
    import app.utils.config as cfg
    monkeypatch.setenv("EMAIL_USERNAME", "sender@memorynest.local")
    monkeypatch.setenv("EMAIL_APP_PASSWORD", "secretpass")
    monkeypatch.setenv("RECIPIENT_EMAIL", "global_fallback@example.com")
    monkeypatch.setattr(cfg, "EMAIL_USERNAME", "sender@memorynest.local")
    monkeypatch.setattr(cfg, "EMAIL_APP_PASSWORD", "secretpass")
    monkeypatch.setattr(cfg, "RECIPIENT_EMAIL", "global_fallback@example.com")

    cookies = _register_and_login(client, "alice", "password123", email="alice@personal.org")
    event_id = _upload_and_extract(client, cookies, "flight.txt", b"Flight to Delhi on 2026-11-20")

    resp = client.post(f"/api/events/{event_id}/confirm", json={"remind_at": "2026-11-19 10:00:00"}, cookies=cookies)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "confirmed"
    assert data["email_status"] == "sent"

    # Verify SMTP received message addressed to alice's email
    assert len(mock_smtp.sent_messages) == 1
    msg = mock_smtp.sent_messages[0]
    assert msg["To"] == "alice@personal.org"
    assert msg["From"] == "sender@memorynest.local"
    assert "Reminder Confirmation:" in msg["Subject"]
    content = msg.get_content()
    assert "flight.txt" in content
    assert "Flight to Delhi" in content
    assert "2026-11-19 10:00:00" in content

    # Verify notification log
    logs = NotificationLogRepository().recent(1)
    assert len(logs) == 1
    assert logs[0].kind == "confirmation"
    assert logs[0].success == 1
    assert logs[0].detail == "sent"

    # Verify reminder was created
    reminders = client.get("/api/reminders", cookies=cookies).json()
    assert len(reminders) == 1
    assert reminders[0]["status"] == "scheduled"


def test_confirm_email_status_no_email(client, mock_smtp, monkeypatch):
    """User without email gets email_status='no_email' and reminder is still created."""
    import app.utils.config as cfg
    monkeypatch.setenv("EMAIL_USERNAME", "sender@memorynest.local")
    monkeypatch.setenv("EMAIL_APP_PASSWORD", "secretpass")
    monkeypatch.setattr(cfg, "EMAIL_USERNAME", "sender@memorynest.local")
    monkeypatch.setattr(cfg, "EMAIL_APP_PASSWORD", "secretpass")

    cookies = _register_and_login(client, "noemailuser", "password123")
    event_id = _upload_and_extract(client, cookies, "doc.txt", b"Interview on 2026-12-01")

    resp = client.post(f"/api/events/{event_id}/confirm", json={}, cookies=cookies)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "confirmed"
    assert data["email_status"] == "no_email"

    # SMTP not invoked
    assert len(mock_smtp.sent_messages) == 0

    # Reminder created
    reminders = client.get("/api/reminders", cookies=cookies).json()
    assert len(reminders) == 1
    assert reminders[0]["status"] == "scheduled"

    # No failed logs created
    logs = NotificationLogRepository().recent(5)
    assert len(logs) == 0


def test_confirm_email_status_not_configured(client, mock_smtp, monkeypatch):
    """User with email but unconfigured SMTP gets email_status='not_configured'."""
    import app.utils.config as cfg
    monkeypatch.setenv("EMAIL_USERNAME", "")
    monkeypatch.setenv("EMAIL_APP_PASSWORD", "")
    monkeypatch.setattr(cfg, "EMAIL_USERNAME", "")
    monkeypatch.setattr(cfg, "EMAIL_APP_PASSWORD", "")

    cookies = _register_and_login(client, "configureduser", "password123", email="user@test.org")
    event_id = _upload_and_extract(client, cookies, "doc.txt", b"Dentist appointment on 2026-12-15")

    resp = client.post(f"/api/events/{event_id}/confirm", json={}, cookies=cookies)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "confirmed"
    assert data["email_status"] == "not_configured"

    # SMTP not called
    assert len(mock_smtp.sent_messages) == 0

    # Reminder still created
    reminders = client.get("/api/reminders", cookies=cookies).json()
    assert len(reminders) == 1
    assert reminders[0]["status"] == "scheduled"

    # Row in notification_logs with kind="confirmation", success=0
    logs = NotificationLogRepository().recent(1)
    assert len(logs) == 1
    assert logs[0].kind == "confirmation"
    assert logs[0].success == 0
    assert "SMTP not configured" in logs[0].detail


def test_confirm_email_status_failed(client, monkeypatch):
    """When SMTP raises, reminder is still created, 200 returned, and email_status='failed'."""
    import app.utils.config as cfg
    monkeypatch.setenv("EMAIL_USERNAME", "sender@memorynest.local")
    monkeypatch.setenv("EMAIL_APP_PASSWORD", "secretpass")
    monkeypatch.setattr(cfg, "EMAIL_USERNAME", "sender@memorynest.local")
    monkeypatch.setattr(cfg, "EMAIL_APP_PASSWORD", "secretpass")

    class FailingSMTP:
        def __init__(self, host, port, timeout=30):
            pass
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass
        def starttls(self):
            pass
        def login(self, user, password):
            pass
        def send_message(self, msg):
            raise smtplib.SMTPConnectError(421, b"Connection refused")

    monkeypatch.setattr(smtplib, "SMTP", FailingSMTP)

    cookies = _register_and_login(client, "failuser", "password123", email="failuser@test.org")
    event_id = _upload_and_extract(client, cookies, "event.txt", b"Conference on 2026-12-20")

    resp = client.post(f"/api/events/{event_id}/confirm", json={}, cookies=cookies)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "confirmed"
    assert data["email_status"] == "failed"

    # Reminder was still created
    reminders = client.get("/api/reminders", cookies=cookies).json()
    assert len(reminders) == 1
    assert reminders[0]["status"] == "scheduled"

    # Failure logged in notification_logs
    logs = NotificationLogRepository().recent(1)
    assert len(logs) == 1
    assert logs[0].kind == "confirmation"
    assert logs[0].success == 0
    assert "Connection refused" in logs[0].detail or "SMTP" in logs[0].detail


def test_check_due_reminders_uses_user_email(client, mock_smtp, monkeypatch):
    """Check-due reminders sends to the user's email, not the global fallback."""
    import app.utils.config as cfg
    monkeypatch.setenv("EMAIL_USERNAME", "sender@memorynest.local")
    monkeypatch.setenv("EMAIL_APP_PASSWORD", "secretpass")
    monkeypatch.setenv("RECIPIENT_EMAIL", "global_fallback@example.com")
    monkeypatch.setattr(cfg, "EMAIL_USERNAME", "sender@memorynest.local")
    monkeypatch.setattr(cfg, "EMAIL_APP_PASSWORD", "secretpass")
    monkeypatch.setattr(cfg, "RECIPIENT_EMAIL", "global_fallback@example.com")

    cookies = _register_and_login(client, "dueuser", "password123", email="due_user@custom.com")
    event_id = _upload_and_extract(client, cookies, "doc.txt", b"Meeting on 2026-12-25")

    # Confirm with past time so it's immediately due
    client.post(f"/api/events/{event_id}/confirm", json={"remind_at": "2020-01-01 09:00:00"}, cookies=cookies)

    # Clear mock smtp messages from confirmation
    mock_smtp.sent_messages.clear()

    # Trigger due reminder check
    resp = client.post("/api/reminders/check", cookies=cookies)
    assert resp.status_code == 200
    data = resp.json()
    assert data["configured"] is True
    assert data["sent"] == 1
    assert data["failed"] == 0

    # Verify recipient was due_user@custom.com, NOT global_fallback@example.com
    assert len(mock_smtp.sent_messages) == 1
    assert mock_smtp.sent_messages[0]["To"] == "due_user@custom.com"


def test_send_reminder_email_recipient_parameter_and_fallback(mock_smtp, monkeypatch):
    """Unit tests for send_reminder_email: explicit to_address vs legacy fallback."""
    import app.utils.config as cfg
    monkeypatch.setenv("EMAIL_USERNAME", "sender@test.local")
    monkeypatch.setenv("EMAIL_APP_PASSWORD", "pass123")
    monkeypatch.setenv("RECIPIENT_EMAIL", "legacy@fallback.com")
    monkeypatch.setattr(cfg, "EMAIL_USERNAME", "sender@test.local")
    monkeypatch.setattr(cfg, "EMAIL_APP_PASSWORD", "pass123")
    monkeypatch.setattr(cfg, "RECIPIENT_EMAIL", "legacy@fallback.com")

    mock_smtp.sent_messages.clear()

    # Explicit to_address
    ok, detail = email_service.send_reminder_email("Subj", "Body", to_address="explicit@user.com")
    assert ok is True
    assert mock_smtp.sent_messages[0]["To"] == "explicit@user.com"

    # Fallback to RECIPIENT_EMAIL
    mock_smtp.sent_messages.clear()
    ok, detail = email_service.send_reminder_email("Subj", "Body")
    assert ok is True
    assert mock_smtp.sent_messages[0]["To"] == "legacy@fallback.com"

    # Missing recipient completely
    monkeypatch.setenv("RECIPIENT_EMAIL", "")
    monkeypatch.setattr(cfg, "RECIPIENT_EMAIL", "")
    ok, detail = email_service.send_reminder_email("Subj", "Body")
    assert ok is False
    assert "not configured" in detail
