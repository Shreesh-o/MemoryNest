"""Regression tests for Phase 4: ARC-05 (deletion responsibilities) and ARC-07/08 (search scoping, calendar queries, dashboard deadlines)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.database.repositories import (
    ChunkRepository,
    DocumentRepository,
    EventRepository,
    ReminderRepository,
    UserRepository,
)
from app.services import document_service, search_service
from app.services.calendar_service import get_calendar_items
from app.services.dashboard_service import get_dashboard


@pytest.fixture
def test_user():
    user_repo = UserRepository()
    return user_repo.create("arch_user", "pw_hash", "arch@example.com")


def test_deletion_coordination_success(tmp_path, test_user):
    """Verifies document_service.delete_document coordinates vector, cache, db, and disk cleanup."""
    doc_repo = DocumentRepository()
    chunk_repo = ChunkRepository()

    # Create dummy stored file
    file_path = tmp_path / "dummy.txt"
    file_path.write_text("sample content")

    doc = doc_repo.create(test_user.id, "dummy.txt", str(file_path), "txt", 14)
    chunk = chunk_repo.create(doc.id, test_user.id, 0, "sample content", 5, "chroma-dummy-0")

    # Invalidate cache stub / test cache file
    from app.services.text_cache_service import get_text_cache_dir
    cache_file = get_text_cache_dir() / f"{doc.id}.txt"
    cache_file.write_text("cached content")

    # Perform deletion
    document_service.delete_document(test_user.id, doc.id)

    # 1. SQLite doc row deleted
    assert doc_repo.get_by_id(doc.id, test_user.id) is None
    # 2. SQLite chunks deleted
    assert chunk_repo.list_for_document(doc.id, test_user.id) == []
    # 3. Cache file deleted
    assert not cache_file.exists()
    # 4. Stored file on disk deleted
    assert not file_path.exists()


def test_deletion_failure_preserves_sqlite_and_file(tmp_path, test_user):
    """If VectorService fails, RuntimeError propagates and SQLite rows & files are preserved."""
    from app.services import vector_service

    doc_repo = DocumentRepository()
    chunk_repo = ChunkRepository()

    file_path = tmp_path / "preserve.txt"
    file_path.write_text("keep this file")

    doc = doc_repo.create(test_user.id, "preserve.txt", str(file_path), "txt", 14)
    chunk = chunk_repo.create(doc.id, test_user.id, 0, "keep this file", 5, "chroma-preserve-0")

    vs = vector_service.get_vector_service()
    with patch.object(vs, "delete_document", side_effect=RuntimeError("Vector DB unavailable")):
        with pytest.raises(RuntimeError, match="Vector DB unavailable"):
            document_service.delete_document(test_user.id, doc.id)

    # Data must be preserved for repair/retry
    assert doc_repo.get_by_id(doc.id, test_user.id) is not None
    assert len(chunk_repo.list_for_document(doc.id, test_user.id)) == 1
    assert file_path.exists()


def test_document_scoped_semantic_search(test_user):
    """Verifies that search_service.search respects document_ids filtering."""
    from app.services import vector_service

    vs = vector_service.get_vector_service()

    with patch.object(vs, "query", return_value=[]) as mock_query:
        search_service.search(test_user.id, "test query", top_k=5, document_ids=[101, 102])
        mock_query.assert_called_once()
        _, kwargs = mock_query.call_args
        assert kwargs["document_ids"] == [101, 102]
        assert kwargs["top_k"] == 5


def test_calendar_service_avoids_n_plus_one_queries(test_user):
    """Verifies calendar_service uses batch event loading for reminders instead of querying per reminder."""
    ev_repo = EventRepository()
    rem_repo = ReminderRepository()

    # Create 3 events outside the range (e.g. past dates)
    ev1 = ev_repo.create(test_user.id, "Event 1", event_date="2025-01-01")
    ev2 = ev_repo.create(test_user.id, "Event 2", event_date="2025-01-02")
    ev3 = ev_repo.create(test_user.id, "Event 3", event_date="2025-01-03")

    # Create 3 reminders inside the range (2026-11-01 to 2026-11-10) pointing to those events
    rem_repo.create(test_user.id, ev1.id, "2026-11-02 09:00:00", subject="Remind 1")
    rem_repo.create(test_user.id, ev2.id, "2026-11-03 09:00:00", subject="Remind 2")
    rem_repo.create(test_user.id, ev3.id, "2026-11-04 09:00:00", subject="Remind 3")

    with patch.object(EventRepository, "get_by_id", side_effect=AssertionError("get_by_id called in loop!")):
        items = get_calendar_items(test_user.id, "2026-11-01", "2026-11-10")

    assert len(items) == 3
    assert all(item.kind == "reminder" for item in items)


def test_dashboard_upcoming_deadlines_excludes_past_dates(test_user):
    """Verifies upcoming_deadlines in dashboard excludes past dates and retains future dates."""
    ev_repo = EventRepository()

    # Past event: 2020-01-01
    past_ev = ev_repo.create(test_user.id, "Past Deadline", event_date="2020-01-01")
    ev_repo.set_status(past_ev.id, test_user.id, "confirmed")

    # Future event: 2099-12-31
    future_ev = ev_repo.create(test_user.id, "Future Deadline", event_date="2099-12-31")
    ev_repo.set_status(future_ev.id, test_user.id, "confirmed")

    dashboard = get_dashboard(test_user.id)
    deadline_texts = [d.event_text for d in dashboard.upcoming_deadlines]

    assert "Future Deadline" in deadline_texts
    assert "Past Deadline" not in deadline_texts
