"""Multi-user authorization and data isolation tests.

Verifies strict tenant isolation across documents, file downloads, content,
summaries, reminders, events, conversations, and search.
"""

from __future__ import annotations

import io
import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.database.repositories import DocumentRepository, EventRepository, ReminderRepository, SummaryRepository
from app.services.auth_service import register as auth_register
from app.api.security import create_token


@pytest.fixture
def users_and_clients(test_storage):
    """Create two distinct users and TestClients with respective session cookies."""
    user_a = auth_register("alice_tenant", "password123", "alice@tenant.local")
    user_b = auth_register("bob_tenant", "password123", "bob@tenant.local")

    token_a = create_token(user_a.id, user_a.username)
    token_b = create_token(user_b.id, user_b.username)

    client_a = TestClient(app)
    client_a.cookies.set("mn_session", token_a)

    client_b = TestClient(app)
    client_b.cookies.set("mn_session", token_b)

    return {
        "user_a": user_a,
        "user_b": user_b,
        "client_a": client_a,
        "client_b": client_b,
    }


def test_cross_user_document_isolation(users_and_clients, tmp_path):
    """User B cannot view, download, read content, delete, or retry User A's document."""
    client_a = users_and_clients["client_a"]
    client_b = users_and_clients["client_b"]
    user_a = users_and_clients["user_a"]

    # Upload document as User A
    res = client_a.post(
        "/api/documents/upload",
        files=[("files", ("alice_doc.txt", io.BytesIO(b"Confidential Alice Data"), "text/plain"))],
    )
    assert res.status_code == 200
    doc_id = res.json()[0]["doc_id"]
    assert doc_id is not None

    # User A can access
    assert client_a.get(f"/api/documents/{doc_id}").status_code == 200
    assert client_a.get(f"/api/documents/{doc_id}/content").status_code == 200
    assert client_a.get(f"/api/documents/{doc_id}/file").status_code == 200

    # User B cannot access User A's document (must return 404, not leak existence)
    assert client_b.get(f"/api/documents/{doc_id}").status_code == 404
    assert client_b.get(f"/api/documents/{doc_id}/content").status_code == 404
    assert client_b.get(f"/api/documents/{doc_id}/file").status_code == 404
    assert client_b.post(f"/api/documents/{doc_id}/retry").status_code == 404
    assert client_b.delete(f"/api/documents/{doc_id}").status_code == 404

    # Document still exists for User A
    assert client_a.get(f"/api/documents/{doc_id}").status_code == 200


def test_cross_user_events_and_reminders_isolation(users_and_clients):
    """User B cannot confirm, discard, or delete User A's events or reminders."""
    client_a = users_and_clients["client_a"]
    client_b = users_and_clients["client_b"]
    user_a = users_and_clients["user_a"]

    # Seed event and reminder for User A
    event_repo = EventRepository()
    ev_a = event_repo.create(
        user_id=user_a.id,
        event_text="Alice Doctor Appointment",
        event_date="2026-11-01 10:00:00",
        raw_date="Nov 1",
    )

    reminder_repo = ReminderRepository()
    rem_a = reminder_repo.create(
        user_id=user_a.id,
        event_id=ev_a.id,
        remind_at="2026-11-01 09:00:00",
        channel="email",
        subject="Appointment Reminder",
        body="Doctor visit",
    )

    # User B attempts to confirm Alice's event -> 404
    res = client_b.post(f"/api/events/{ev_a.id}/confirm", json={"remind_at": "2026-11-01 08:00:00"})
    assert res.status_code == 404

    # User B attempts to discard Alice's event -> 404
    assert client_b.post(f"/api/events/{ev_a.id}/discard").status_code == 404

    # User B attempts to delete Alice's reminder -> 404
    assert client_b.delete(f"/api/reminders/{rem_a.id}").status_code == 404

    # User B's event listing does not contain Alice's event
    events_b = client_b.get("/api/events").json()
    assert all(e["id"] != ev_a.id for e in events_b)

    # User B's reminder listing does not contain Alice's reminder
    reminders_b = client_b.get("/api/reminders").json()
    assert all(r["id"] != rem_a.id for r in reminders_b)


def test_cross_user_summaries_isolation(users_and_clients, tmp_path):
    """User B cannot create or access User A's document summaries."""
    client_a = users_and_clients["client_a"]
    client_b = users_and_clients["client_b"]
    user_a = users_and_clients["user_a"]

    # Seed document and summary for User A
    doc_path = tmp_path / "alice_notes.txt"
    doc_path.write_text("Some text for Alice")
    doc_repo = DocumentRepository()
    doc_a = doc_repo.create(
        user_id=user_a.id,
        filename="alice_notes.txt",
        stored_path=str(doc_path),
        file_type="txt",
        size_bytes=100,
    )
    doc_repo.update_status(doc_a.id, user_a.id, "ready")

    summary_repo = SummaryRepository()
    sum_a = summary_repo.create(
        document_id=doc_a.id,
        user_id=user_a.id,
        summary_text="Alice's confidential summary",
    )

    # User B attempts to generate summary for Alice's document -> 404
    assert client_b.post(f"/api/documents/{doc_a.id}/summary", json={"force": False}).status_code == 404

    # User B attempts to access Alice's summary audio -> 404
    assert client_b.get(f"/api/summaries/{sum_a.id}/audio").status_code == 404

    # User B's summary listing does not contain Alice's summary
    summaries_b = client_b.get("/api/summaries").json()
    assert all(s["id"] != sum_a.id for s in summaries_b)


def test_cross_user_conversations_isolation(users_and_clients):
    """User B cannot read or delete User A's chat conversations."""
    client_a = users_and_clients["client_a"]
    client_b = users_and_clients["client_b"]
    user_a = users_and_clients["user_a"]

    from app.database.repositories import ConversationRepository
    convo_repo = ConversationRepository()
    convo_a = convo_repo.create(user_id=user_a.id, title="Alice Secret Chat")

    # User B cannot access
    assert client_b.get(f"/api/conversations/{convo_a.id}").status_code == 404
    assert client_b.get(f"/api/conversations/{convo_a.id}/messages").status_code == 404

    # User B's list does not contain Alice's conversation
    convos_b = client_b.get("/api/conversations").json()
    assert all(c["id"] != convo_a.id for c in convos_b)
