"""Tests for Google Calendar synchronization on confirm, cancel, and resync."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app
from app.database.models import User
from app.database.repositories import (
    EventRepository,
    GoogleConnectionRepository,
    ReminderRepository,
    UserRepository,
)
from app.utils import config
from app.utils.security import encrypt_token


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    """Use an isolated temp database for each test."""
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

    monkeypatch.setattr(config, "GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setattr(config, "GOOGLE_CLIENT_SECRET", "test-client-secret")

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


def _register_and_login(client: TestClient, username: str, password: str = "pass123") -> tuple[dict, User]:
    resp = client.post("/api/auth/register", json={"username": username, "password": password})
    assert resp.status_code == 201
    resp = client.post("/api/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200
    user = UserRepository().get_by_username(username)
    assert user is not None
    return dict(resp.cookies), user


def _connect_google(user_id: int, email: str = "user@gmail.com") -> None:
    GoogleConnectionRepository().upsert(
        user_id=user_id,
        google_email=email,
        refresh_token_encrypted=encrypt_token("mock-refresh-token"),
        scope="openid,calendar.events",
    )


def test_create_event_timed_and_all_day(client):
    """Confirming an event when connected creates a Google Calendar event with correct fields."""
    cookies, user = _register_and_login(client, "alice")
    _connect_google(user.id)

    ev_repo = EventRepository()
    # 1. Timed event
    ev_timed = ev_repo.create(
        user.id,
        "Doctor appointment",
        event_date="2026-11-20 14:00:00",
    )

    mock_service = MagicMock()
    mock_events = mock_service.events.return_value
    mock_insert = mock_events.insert.return_value
    mock_insert.execute.return_value = {"id": "gcal_timed_123"}

    with patch("app.services.google_calendar_service.get_calendar_client", return_value=mock_service):
        resp = client.post(
            f"/api/events/{ev_timed.id}/confirm",
            json={"remind_at": "2026-11-20 13:30:00"},  # 30 min before
            cookies=cookies,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "confirmed"
        assert data["google_status"] == "synced"

        # Verify Google API insert call
        mock_events.insert.assert_called_once()
        _, kwargs = mock_events.insert.call_args
        body = kwargs["body"]
        assert body["summary"] == "Doctor appointment"
        assert "Created by MemoryNest" in body["description"]
        assert body["start"]["timeZone"] == "Asia/Kolkata"
        assert "2026-11-20T14:00:00" in body["start"]["dateTime"]
        assert body["reminders"]["overrides"] == [{"method": "popup", "minutes": 30}]

    # Check reminder in DB and GET /api/reminders
    reminders = client.get("/api/reminders", cookies=cookies).json()
    assert len(reminders) == 1
    rem = reminders[0]
    assert rem["sync_status"] == "synced"
    assert rem["google_event_id"] == "gcal_timed_123"
    assert rem["sync_error"] is None

    # Check calendar items response includes sync_status
    cal_resp = client.get("/api/calendar/items?start=2026-11-01&end=2026-11-30", cookies=cookies)
    assert cal_resp.status_code == 200
    cal_items = cal_resp.json()
    assert len(cal_items) >= 1
    rem_item = next(it for it in cal_items if it["kind"] == "reminder")
    assert rem_item["sync_status"] == "synced"

    # 2. All-day event
    ev_all_day = ev_repo.create(
        user.id,
        "Annual Conference",
        event_date="2026-11-25",
    )
    mock_events.reset_mock()
    mock_insert.execute.return_value = {"id": "gcal_allday_456"}

    with patch("app.services.google_calendar_service.get_calendar_client", return_value=mock_service):
        resp = client.post(
            f"/api/events/{ev_all_day.id}/confirm",
            json={"remind_at": "2026-11-24 10:00:00"},
            cookies=cookies,
        )
        assert resp.status_code == 200
        assert resp.json()["google_status"] == "synced"

        mock_events.insert.assert_called_once()
        _, kwargs = mock_events.insert.call_args
        body = kwargs["body"]
        assert body["summary"] == "Annual Conference"
        assert body["start"] == {"date": "2026-11-25"}
        assert body["end"] == {"date": "2026-11-26"}


def test_update_not_duplicate_idempotency(client):
    """If google_event_id already exists, resync updates existing event rather than inserting a duplicate."""
    cookies, user = _register_and_login(client, "bob")
    _connect_google(user.id)

    ev = EventRepository().create(user.id, "Team Standup", event_date="2026-11-15 10:00:00")
    rem = ReminderRepository().create(
        user.id,
        ev.id,
        "2026-11-15 09:45:00",
        google_event_id="existing_gcal_id_789",
        sync_status="failed",
    )

    mock_service = MagicMock()
    mock_events = mock_service.events.return_value
    mock_update = mock_events.update.return_value
    mock_update.execute.return_value = {"id": "existing_gcal_id_789"}

    with patch("app.services.google_calendar_service.get_calendar_client", return_value=mock_service):
        resp = client.post(f"/api/reminders/{rem.id}/sync", cookies=cookies)
        assert resp.status_code == 200
        data = resp.json()
        assert data["sync_status"] == "synced"
        assert data["google_event_id"] == "existing_gcal_id_789"

        # Ensure update was called, NOT insert
        mock_events.update.assert_called_once()
        _, kwargs = mock_events.update.call_args
        assert kwargs["eventId"] == "existing_gcal_id_789"
        mock_events.insert.assert_not_called()


def test_delete_on_cancel(client):
    """Cancelling a reminder deletes the Google Calendar event and removes reminder row."""
    cookies, user = _register_and_login(client, "charlie")
    _connect_google(user.id)

    ev = EventRepository().create(user.id, "Client pitch", event_date="2026-11-18 11:00:00")
    rem = ReminderRepository().create(
        user.id,
        ev.id,
        "2026-11-18 10:00:00",
        google_event_id="gcal_to_delete_999",
        sync_status="synced",
    )

    mock_service = MagicMock()
    mock_events = mock_service.events.return_value
    mock_delete = mock_events.delete.return_value
    mock_delete.execute.return_value = {}

    with patch("app.services.google_calendar_service.get_calendar_client", return_value=mock_service):
        resp = client.delete(f"/api/reminders/{rem.id}", cookies=cookies)
        assert resp.status_code == 204

        mock_events.delete.assert_called_once_with(
            calendarId="primary",
            eventId="gcal_to_delete_999",
        )

    # Reminder is deleted
    assert ReminderRepository().get_by_id(rem.id, user.id) is None
    # Event reverted to pending
    updated_ev = EventRepository().get_by_id(ev.id, user.id)
    assert updated_ev.status == "pending"


def test_google_failure_does_not_break_confirm(client):
    """Google Calendar failure must NEVER break confirming an event; records sync_status='failed'."""
    cookies, user = _register_and_login(client, "dave")
    _connect_google(user.id)

    ev = EventRepository().create(user.id, "Urgent meeting", event_date="2026-11-10 15:00:00")

    mock_service = MagicMock()
    mock_events = mock_service.events.return_value
    mock_events.insert.return_value.execute.side_effect = RuntimeError("503 Service Unavailable")

    with patch("app.services.google_calendar_service.get_calendar_client", return_value=mock_service):
        resp = client.post(
            f"/api/events/{ev.id}/confirm",
            json={"remind_at": "2026-11-10 14:00:00"},
            cookies=cookies,
        )
        # HTTP 200: Confirm succeeded despite Google failure
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "confirmed"
        assert data["google_status"] == "failed"

    # Event in DB is confirmed
    ev_in_db = EventRepository().get_by_id(ev.id, user.id)
    assert ev_in_db.status == "confirmed"

    # Reminder recorded with failed sync status and error message
    rems = ReminderRepository().list_for_user(user.id)
    assert len(rems) == 1
    assert rems[0].sync_status == "failed"
    assert "503 Service Unavailable" in (rems[0].sync_error or "")


def test_google_failure_does_not_break_cancel(client):
    """Google failure during cancel must NEVER block reminder cancellation."""
    cookies, user = _register_and_login(client, "eve")
    _connect_google(user.id)

    ev = EventRepository().create(user.id, "Interview", event_date="2026-11-12 16:00:00")
    rem = ReminderRepository().create(
        user.id,
        ev.id,
        "2026-11-12 15:00:00",
        google_event_id="gcal_err_id",
        sync_status="synced",
    )

    mock_service = MagicMock()
    mock_events = mock_service.events.return_value
    mock_events.delete.return_value.execute.side_effect = RuntimeError("Google connection timeout")

    with patch("app.services.google_calendar_service.get_calendar_client", return_value=mock_service):
        resp = client.delete(f"/api/reminders/{rem.id}", cookies=cookies)
        assert resp.status_code == 204

    # Reminder row is deleted and event reverted
    assert ReminderRepository().get_by_id(rem.id, user.id) is None
    assert EventRepository().get_by_id(ev.id, user.id).status == "pending"


def test_not_connected_path(client):
    """When user is not connected, confirm schedules reminder with sync_status='not_connected'."""
    cookies, user = _register_and_login(client, "frank")
    # Frank has not connected to Google

    ev = EventRepository().create(user.id, "Dentist", event_date="2026-11-14 09:00:00")

    with patch("app.services.google_calendar_service.get_calendar_client") as mock_client:
        resp = client.post(f"/api/events/{ev.id}/confirm", json={}, cookies=cookies)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "confirmed"
        assert data["google_status"] == "not_connected"
        mock_client.assert_not_called()

    rems = ReminderRepository().list_for_user(user.id)
    assert len(rems) == 1
    assert rems[0].sync_status == "not_connected"
    assert rems[0].google_event_id is None
    assert rems[0].sync_error is None


def test_user_isolation(client):
    """User B cannot sync or delete User A's reminders."""
    cookies_a, user_a = _register_and_login(client, "usera")
    cookies_b, user_b = _register_and_login(client, "userb")

    _connect_google(user_a.id, email="a@gmail.com")
    _connect_google(user_b.id, email="b@gmail.com")

    ev_a = EventRepository().create(user_a.id, "User A Secret", event_date="2026-11-22 10:00:00")
    rem_a = ReminderRepository().create(
        user_a.id,
        ev_a.id,
        "2026-11-22 09:00:00",
        google_event_id="usera_gcal_id",
        sync_status="synced",
    )

    mock_service = MagicMock()
    with patch("app.services.google_calendar_service.get_calendar_client", return_value=mock_service):
        # User B tries to resync User A's reminder -> 404
        resp = client.post(f"/api/reminders/{rem_a.id}/sync", cookies=cookies_b)
        assert resp.status_code == 404

        # User B tries to delete User A's reminder -> 404
        resp = client.delete(f"/api/reminders/{rem_a.id}", cookies=cookies_b)
        assert resp.status_code == 404

        # Google client operations were never called on behalf of User B for User A's items
        mock_service.events.return_value.delete.assert_not_called()
        mock_service.events.return_value.update.assert_not_called()

    # User A's reminder remains intact
    assert ReminderRepository().get_by_id(rem_a.id, user_a.id) is not None


def test_retry_on_401_marks_disconnected(client):
    """When a 401 or token revocation occurs, the connection is marked disconnected."""
    cookies, user = _register_and_login(client, "grace")
    _connect_google(user.id)

    ev = EventRepository().create(user.id, "Board meeting", event_date="2026-11-30 14:00:00")

    mock_resp = MagicMock()
    mock_resp.status = 401
    from googleapiclient.errors import HttpError
    http_401 = HttpError(resp=mock_resp, content=b"Unauthorized")

    mock_service = MagicMock()
    mock_events = mock_service.events.return_value
    mock_events.insert.return_value.execute.side_effect = http_401

    # First get_calendar_client returns client, but during execute() it raises 401; retry refresh also fails
    with patch(
        "app.services.google_calendar_service.get_calendar_client",
        side_effect=[mock_service, None],
    ):
        resp = client.post(f"/api/events/{ev.id}/confirm", json={}, cookies=cookies)
        assert resp.status_code == 200
        # Google status was failed/not_connected
        assert resp.json()["status"] == "confirmed"

    # Connection repository should now have deleted grace's connection
    assert GoogleConnectionRepository().get_by_user_id(user.id) is None


def test_document_name_in_description_and_minute_clamping(client):
    """Event description includes source document filename, and reminder minutes are clamped."""
    from app.database.repositories import DocumentRepository
    cookies, user = _register_and_login(client, "helen")
    _connect_google(user.id)

    doc = DocumentRepository().create(
        user_id=user.id,
        filename="Syllabus_2026.pdf",
        stored_path="/fake/path",
        file_type="pdf",
        status="ready",
    )

    ev_repo = EventRepository()
    ev = ev_repo.create(
        user.id,
        "Final Exam",
        document_id=doc.id,
        event_date="2026-12-01 10:00:00",
    )

    mock_service = MagicMock()
    mock_events = mock_service.events.return_value
    mock_events.insert.return_value.execute.return_value = {"id": "gcal_exam_1"}

    with patch("app.services.google_calendar_service.get_calendar_client", return_value=mock_service):
        # 1. Remind at 5 weeks before (more than 40320 minutes -> should clamp to 40320)
        resp = client.post(
            f"/api/events/{ev.id}/confirm",
            json={"remind_at": "2026-10-20 10:00:00"},  # ~6 weeks before
            cookies=cookies,
        )
        assert resp.status_code == 200
        _, kwargs = mock_events.insert.call_args
        body = kwargs["body"]
        assert "Syllabus_2026.pdf" in body["description"]
        assert "Created by MemoryNest" in body["description"]
        assert body["reminders"]["overrides"][0]["minutes"] == 40320


def test_delete_event_handles_404_already_deleted(client):
    """If the Google event was already deleted on Google Calendar (404/410), cancel succeeds cleanly."""
    cookies, user = _register_and_login(client, "ian")
    _connect_google(user.id)

    ev = EventRepository().create(user.id, "Workshop", event_date="2026-11-28 09:00:00")
    rem = ReminderRepository().create(
        user.id,
        ev.id,
        "2026-11-28 08:30:00",
        google_event_id="gcal_deleted_remotely",
        sync_status="synced",
    )

    mock_resp = MagicMock()
    mock_resp.status = 404
    from googleapiclient.errors import HttpError
    http_404 = HttpError(resp=mock_resp, content=b"Not Found")

    mock_service = MagicMock()
    mock_service.events.return_value.delete.return_value.execute.side_effect = http_404

    with patch("app.services.google_calendar_service.get_calendar_client", return_value=mock_service):
        resp = client.delete(f"/api/reminders/{rem.id}", cookies=cookies)
        assert resp.status_code == 204

    assert ReminderRepository().get_by_id(rem.id, user.id) is None

