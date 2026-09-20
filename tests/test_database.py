"""Unit tests for the SQLite layer (schema + repositories)."""

from __future__ import annotations

import pytest

from app.database.database import init_db
from app.database.repositories import (
    ConversationRepository,
    EventRepository,
    MessageRepository,
    NotificationLogRepository,
    ReminderRepository,
    SummaryRepository,
    UserRepository,
    ChunkRepository,
    DocumentRepository,
)


@pytest.fixture()
def db(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    return db_path


@pytest.fixture()
def repos(db, monkeypatch):
    monkeypatch.setattr("app.database.database.DB_PATH", db)

    user = UserRepository().create("alice", "hash-alice", "alice@example.com")
    return {
        "user": user,
        "users": UserRepository(),
        "documents": DocumentRepository(),
        "chunks": ChunkRepository(),
        "conversations": ConversationRepository(),
        "messages": MessageRepository(),
        "summaries": SummaryRepository(),
        "events": EventRepository(),
        "reminders": ReminderRepository(),
        "logs": NotificationLogRepository(),
    }


def test_user_crud(repos):
    user = repos["users"].get_by_username("alice")
    assert user is not None and user.id == repos["user"].id
    assert user.username == "alice"
    assert repos["users"].get_by_username("nobody") is None
    assert len(repos["users"].list_all()) == 1
    repos["users"].delete(user.id)
    assert repos["users"].get_by_id(user.id) is None


def test_document_crud_and_user_isolation(repos):
    doc = repos["documents"].create(
        repos["user"].id, "report.pdf", "/tmp/report.pdf", "pdf", 1234
    )
    assert doc.id and doc.status == "uploaded"

    # A second user cannot see it.
    other = repos["users"].create("bob", "hash-bob")
    assert repos["documents"].get_by_id(doc.id, other.id) is None
    assert len(repos["documents"].list_for_user(other.id)) == 0

    repos["documents"].update_status(doc.id, repos["user"].id, "error", "bad pdf")
    doc2 = repos["documents"].get_by_id(doc.id, repos["user"].id)
    assert doc2.status == "error" and doc2.error_message == "bad pdf"

    repos["documents"].set_text(doc.id, repos["user"].id, "preview text", 3)
    doc3 = repos["documents"].get_by_id(doc.id, repos["user"].id)
    assert doc3.status == "ready" and doc3.chunk_count == 3 and doc3.text_preview == "preview text"
    assert repos["documents"].count_for_user(repos["user"].id) == 1


def test_chunks(repos):
    doc = repos["documents"].create(repos["user"].id, "a.txt", "/tmp/a.txt", "txt")
    c1 = repos["chunks"].create(doc.id, repos["user"].id, 0, "first chunk", 10, "chroma-0")
    c2 = repos["chunks"].create(doc.id, repos["user"].id, 1, "second chunk", 12, "chroma-1")
    assert c1.chunk_index == 0 and c2.chunk_index == 1

    chunks = repos["chunks"].list_for_document(doc.id, repos["user"].id)
    assert [c.content for c in chunks] == ["first chunk", "second chunk"]

    chroma_ids = repos["chunks"].delete_for_document(doc.id, repos["user"].id)
    assert set(chroma_ids) == {"chroma-0", "chroma-1"}
    assert repos["chunks"].list_for_document(doc.id, repos["user"].id) == []


def test_conversation_and_messages(repos):
    convo = repos["conversations"].create(repos["user"].id, "First chat")
    m1 = repos["messages"].create(convo.id, repos["user"].id, "user", "hello")
    m2 = repos["messages"].create(
        convo.id, repos["user"].id, "assistant", "hi there",
        sources=[{"document": "a.txt", "chunk": 0, "similarity": 0.9}],
    )
    msgs = repos["messages"].list_for_conversation(convo.id, repos["user"].id)
    assert [m.role for m in msgs] == ["user", "assistant"]
    import json
    assert json.loads(m2.sources)[0]["document"] == "a.txt"

    found = repos["messages"].search(repos["user"].id, "hello")
    assert found and found[0].id == m1.id

    convos = repos["conversations"].list_for_user(repos["user"].id)
    assert convos and convos[0].id == convo.id

    repos["conversations"].update_title(convo.id, repos["user"].id, "Renamed")
    assert repos["conversations"].get_by_id(convo.id, repos["user"].id).title == "Renamed"

    # Deleting the conversation cascades to messages.
    repos["conversations"].delete(convo.id, repos["user"].id)
    assert repos["messages"].list_for_conversation(convo.id, repos["user"].id) == []


def test_summaries(repos):
    doc = repos["documents"].create(repos["user"].id, "a.txt", "/tmp/a.txt", "txt")
    s = repos["summaries"].create(doc.id, repos["user"].id, "A summary.")
    assert repos["summaries"].list_for_document(doc.id, repos["user"].id)[0].id == s.id
    repos["summaries"].delete_for_document(doc.id, repos["user"].id)
    assert repos["summaries"].list_for_document(doc.id, repos["user"].id) == []


def test_events_and_reminders(repos):
    ev = repos["events"].create(
        repos["user"].id, "Pay rent", event_date="2026-10-01", raw_date="Oct 1st"
    )
    assert ev.status == "pending"
    repos["events"].set_status(ev.id, repos["user"].id, "confirmed")
    assert repos["events"].get_by_id(ev.id, repos["user"].id).status == "confirmed"

    rem = repos["reminders"].create(
        repos["user"].id, ev.id, "2026-09-30 09:00:00",
        subject="Rent due", body="Pay rent on 2026-10-01",
    )
    assert rem.status == "scheduled"

    # Not due yet.
    assert repos["reminders"].due_scheduled(repos["user"].id, "2026-01-01 00:00:00") == []
    # Due now.
    due = repos["reminders"].due_scheduled(repos["user"].id, "2026-09-30 10:00:00")
    assert due and due[0].id == rem.id
    # Due again after event is unconfirmed -> no longer due.
    repos["events"].set_status(ev.id, repos["user"].id, "pending")
    assert repos["reminders"].due_scheduled(repos["user"].id, "2026-09-30 10:00:00") == []

    repos["events"].set_status(ev.id, repos["user"].id, "confirmed")
    repos["reminders"].set_status(rem.id, repos["user"].id, "sent", "2026-09-30 10:00:01")
    sent = repos["reminders"].get_by_id(rem.id, repos["user"].id)
    assert sent.status == "sent" and sent.sent_at == "2026-09-30 10:00:01"


def test_notification_logs(repos):
    log = repos["logs"].log("email", True, "sent ok", user_id=repos["user"].id)
    assert log.success is True or log.success == 1
    assert repos["logs"].recent(limit=5)[0].id == log.id


def test_cascade_user_delete(repos):
    user = repos["user"]
    doc = repos["documents"].create(user.id, "x.txt", "/tmp/x.txt", "txt")
    repos["chunks"].create(doc.id, user.id, 0, "c", 5, "cid-1")
    convo = repos["conversations"].create(user.id)
    repos["messages"].create(convo.id, user.id, "user", "hi")
    ev = repos["events"].create(user.id, "event")
    repos["reminders"].create(user.id, ev.id, "2026-01-01 00:00:00")

    repos["users"].delete(user.id)
    assert repos["documents"].list_for_user(user.id) == []
    assert repos["conversations"].list_for_user(user.id) == []
    assert repos["events"].list_for_user(user.id) == []
