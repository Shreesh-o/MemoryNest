"""Tests for GET /api/calendar/items endpoint and calendar service."""

from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from app.api.main import create_app
from app.database.repositories import EventRepository, ReminderRepository, UserRepository


@pytest.fixture()
def client(tmp_path):
    import app.utils.config as config_module
    db_path = str(config_module.DB_PATH)
    app = create_app(db_path)
    with TestClient(app) as test_client:
        yield test_client


def _register_and_login(client: TestClient, username: str, password: str = "password123") -> dict:
    resp = client.post("/api/auth/register", json={"username": username, "password": password})
    assert resp.status_code == 201
    resp = client.post("/api/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200
    return dict(resp.cookies)


def test_calendar_items_range_filtering(client):
    """Items inside [start, end] are returned; items outside are excluded."""
    cookies = _register_and_login(client, "rangeuser")
    user = UserRepository().get_by_username("rangeuser")
    assert user is not None

    ev_repo = EventRepository()
    rem_repo = ReminderRepository()

    # Event before range
    ev_repo.create(user.id, "Early event", event_date="2026-09-30")
    # Event inside range (date-only -> all_day = True)
    ev_inside = ev_repo.create(user.id, "Target event", event_date="2026-10-15")
    # Event after range
    ev_repo.create(user.id, "Late event", event_date="2026-11-01")

    # Reminder inside range (all_day = False)
    rem_inside = rem_repo.create(
        user.id,
        event_id=ev_inside.id,
        remind_at="2026-10-20 09:00:00",
        subject="Dentist reminder",
    )
    # Reminder after range
    rem_repo.create(
        user.id,
        event_id=ev_inside.id,
        remind_at="2026-11-05 10:00:00",
        subject="Late reminder",
    )

    resp = client.get("/api/calendar/items?start=2026-10-01&end=2026-10-31", cookies=cookies)
    assert resp.status_code == 200
    items = resp.json()

    assert len(items) == 2
    titles = [it["title"] for it in items]
    assert "Target event" in titles
    assert "Dentist reminder" in titles
    assert "Early event" not in titles
    assert "Late event" not in titles
    assert "Late reminder" not in titles

    # Check fields
    event_item = next(it for it in items if it["kind"] == "event")
    assert event_item["id"] == ev_inside.id
    assert event_item["all_day"] is True
    assert event_item["status"] == "pending"
    assert event_item["date"] == "2026-10-15"
    assert event_item["event_id"] == ev_inside.id

    reminder_item = next(it for it in items if it["kind"] == "reminder")
    assert reminder_item["id"] == rem_inside.id
    assert reminder_item["all_day"] is False
    assert reminder_item["status"] == "scheduled"
    assert reminder_item["event_id"] == ev_inside.id


def test_calendar_items_range_validation(client):
    """Range validation handles malformed dates, start > end, and range > 62 days."""
    cookies = _register_and_login(client, "validuser")

    # Missing parameters
    assert client.get("/api/calendar/items", cookies=cookies).status_code == 422
    assert client.get("/api/calendar/items?start=2026-10-01", cookies=cookies).status_code == 422

    # Malformed dates
    resp1 = client.get("/api/calendar/items?start=invalid&end=2026-10-31", cookies=cookies)
    assert resp1.status_code == 400
    assert "format" in resp1.json()["detail"].lower()

    # start > end
    resp2 = client.get("/api/calendar/items?start=2026-10-31&end=2026-10-01", cookies=cookies)
    assert resp2.status_code == 400
    assert "before or equal" in resp2.json()["detail"].lower()

    # Range > 62 days (e.g. 70 days)
    resp3 = client.get("/api/calendar/items?start=2026-10-01&end=2026-12-15", cookies=cookies)
    assert resp3.status_code == 400
    assert "62 days" in resp3.json()["detail"].lower()


def test_calendar_items_user_isolation(client):
    """User A sees only user A's items; User B sees only user B's items."""
    cookies_a = _register_and_login(client, "usera")
    cookies_b = _register_and_login(client, "userb")

    user_a = UserRepository().get_by_username("usera")
    user_b = UserRepository().get_by_username("userb")

    ev_repo = EventRepository()
    ev_repo.create(user_a.id, "User A meeting", event_date="2026-10-15")
    ev_repo.create(user_b.id, "User B party", event_date="2026-10-15")

    # User A query
    resp_a = client.get("/api/calendar/items?start=2026-10-01&end=2026-10-31", cookies=cookies_a)
    assert resp_a.status_code == 200
    items_a = resp_a.json()
    assert len(items_a) == 1
    assert items_a[0]["title"] == "User A meeting"

    # User B query
    resp_b = client.get("/api/calendar/items?start=2026-10-01&end=2026-10-31", cookies=cookies_b)
    assert resp_b.status_code == 200
    items_b = resp_b.json()
    assert len(items_b) == 1
    assert items_b[0]["title"] == "User B party"


def test_calendar_items_excluded_statuses(client):
    """Includes events pending & confirmed (excludes skipped); includes reminders scheduled & sent (excludes cancelled)."""
    cookies = _register_and_login(client, "statususer")
    user = UserRepository().get_by_username("statususer")

    ev_repo = EventRepository()
    rem_repo = ReminderRepository()

    # Events: pending, confirmed, skipped
    ev_pending = ev_repo.create(user.id, "Pending event", event_date="2026-10-10")
    ev_confirmed = ev_repo.create(user.id, "Confirmed event", event_date="2026-10-11")
    ev_repo.set_status(ev_confirmed.id, user.id, "confirmed")
    ev_skipped = ev_repo.create(user.id, "Skipped event", event_date="2026-10-12")
    ev_repo.set_status(ev_skipped.id, user.id, "skipped")

    # Reminders: scheduled, sent, cancelled
    rem_scheduled = rem_repo.create(user.id, ev_confirmed.id, remind_at="2026-10-11 09:00:00", subject="Scheduled reminder")
    rem_sent = rem_repo.create(user.id, ev_confirmed.id, remind_at="2026-10-11 12:00:00", subject="Sent reminder")
    rem_repo.set_status(rem_sent.id, user.id, "sent", "2026-10-11 12:00:01")
    rem_cancelled = rem_repo.create(user.id, ev_confirmed.id, remind_at="2026-10-11 15:00:00", subject="Cancelled reminder")
    rem_repo.set_status(rem_cancelled.id, user.id, "cancelled")

    resp = client.get("/api/calendar/items?start=2026-10-01&end=2026-10-31", cookies=cookies)
    assert resp.status_code == 200
    items = resp.json()

    titles = [it["title"] for it in items]
    assert "Pending event" in titles
    assert "Confirmed event" in titles
    assert "Scheduled reminder" in titles
    assert "Sent reminder" in titles

    assert "Skipped event" not in titles
    assert "Cancelled reminder" not in titles


def test_calendar_items_unauthenticated_returns_401(client):
    """Unauthenticated access to /api/calendar/items returns 401."""
    resp = client.get("/api/calendar/items?start=2026-10-01&end=2026-10-31")
    assert resp.status_code == 401
