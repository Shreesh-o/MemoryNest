"""Focused regression tests for ARC-01: Full-document text retrieval.

Proves:
1. Summaries process content located beyond character 500 (not capped by text_preview).
2. On-demand reminder extraction finds dates located beyond character 500.
3. Missing original files fall back gracefully to reconstructing from database chunks.
4. Empty or unrecoverable documents fail gracefully without silently returning truncated previews.
5. Strict tenant isolation: one user cannot retrieve another user's document text.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app
from app.database.repositories import (
    ChunkRepository,
    DocumentRepository,
    EventRepository,
    UserRepository,
)
from app.services import (
    ingest_service,
    reminder_flow_service,
    summary_flow_service,
)
from app.services.document_service import get_document_full_text
from app.utils.config import DB_PATH


@pytest.fixture
def client():
    app = create_app(str(DB_PATH))
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def user_a():
    user_repo = UserRepository()
    return user_repo.create("usera", "hashpw123", "usera@example.com")


def _upload_file(user_id: int, filename: str, content: str) -> int:
    """Helper to ingest a document directly using ingest_service."""
    result = ingest_service.ingest_upload(
        user_id=user_id,
        original_name=filename,
        file_bytes=content.encode("utf-8"),
    )
    assert result.status == "ready", f"Ingest failed: {result.message}"
    assert result.doc_id is not None
    return result.doc_id


def test_summary_processes_content_beyond_500_chars(user_a):
    """Proves summaries receive and process full document text beyond character 500.

    Previously, doc.text_preview (capped at 500 chars) was used, truncating all later text.
    """
    filler = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 15  # ~850 chars
    key_fact = "CRITICAL_SECRET_FACT_AT_END: The project budget is 9.5 million dollars."
    full_content = f"{filler}\n\n{key_fact}"
    assert len(full_content) > 900

    doc_id = _upload_file(user_a.id, "long_report.txt", full_content)
    doc = DocumentRepository().get_by_id(doc_id, user_a.id)
    assert doc is not None

    # Verify that text_preview is indeed capped at 500 chars and does NOT have the key fact
    assert len(doc.text_preview) <= 500
    assert key_fact not in doc.text_preview

    # Intercept summarize_document call to verify the full_text argument passed to it
    captured_texts = []
    from app.services import summary_service
    original_summarize = summary_service.summarize_document

    def _mock_summarize(full_text: str, max_chunk_tokens: int = 1200) -> str:
        captured_texts.append(full_text)
        return original_summarize(full_text, max_chunk_tokens=max_chunk_tokens)

    with patch.object(summary_service, "summarize_document", side_effect=_mock_summarize):
        summary = summary_flow_service.get_or_create_summary(user_a.id, doc_id, force=True)

    assert summary is not None
    assert len(captured_texts) == 1
    # Verify the full document text, including content far past character 500, was provided
    assert key_fact in captured_texts[0]
    assert len(captured_texts[0]) > 800


def test_reminder_extracts_date_beyond_500_chars(user_a):
    """Proves on-demand reminder extraction finds dates located past character 500."""
    filler = "This is a document about general architectural principles and team discussions. " * 10
    assert len(filler) > 700

    date_text = "The quarterly board meeting is scheduled for 2026-11-20 at 14:00."
    content = f"{filler}\n\n{date_text}"

    doc_id = _upload_file(user_a.id, "schedule_doc.txt", content)
    doc = DocumentRepository().get_by_id(doc_id, user_a.id)
    assert doc is not None

    # Confirm the 500-char preview has no dates
    assert len(doc.text_preview) <= 500
    assert "2026-11-20" not in doc.text_preview

    # Ingestion already extracts events for the full text, so clear initial events
    # to specifically test on-demand extraction via reminder_flow_service
    ev_repo = EventRepository()
    ev_repo.delete_for_document(doc_id, user_a.id)
    assert ev_repo.list_for_user(user_a.id) == []

    # Run on-demand extraction
    events = reminder_flow_service.extract_events_for_document(user_a.id, doc_id)
    assert len(events) >= 1

    extracted_dates = [e.event_date for e in events]
    assert "2026-11-20" in extracted_dates


def test_missing_file_falls_back_to_database_chunks(user_a):
    """Proves that when the stored file is deleted/missing, text is reconstructed from database chunks."""
    content = (
        "Paragraph One introduces the topic with ample descriptive detail and background. " * 30 + "\n\n" +
        "Paragraph Two elaborates further with specific data points, metrics, and facts. " * 30 + "\n\n" +
        "Paragraph Three concludes the document with closing remarks and implementation instructions. " * 30
    )
    doc_id = _upload_file(user_a.id, "multi_chunk.txt", content)
    doc = DocumentRepository().get_by_id(doc_id, user_a.id)
    assert doc is not None
    assert doc.chunk_count > 1

    # Verify chunks exist in the database
    chunk_repo = ChunkRepository()
    chunks = chunk_repo.list_for_document(doc_id, user_a.id)
    assert len(chunks) == doc.chunk_count

    # Delete the stored file from disk
    stored_path = Path(doc.stored_path)
    assert stored_path.exists()
    stored_path.unlink()
    assert not stored_path.exists()

    # Invalidate/remove any disk text cache file
    from app.services.text_cache_service import invalidate_text_cache
    invalidate_text_cache(doc_id)

    # Full text retrieval must succeed via chunk reconstruction
    recovered_text = get_document_full_text(user_a.id, doc_id)
    assert recovered_text
    assert "Paragraph One introduces the topic" in recovered_text
    assert "Paragraph Two elaborates further" in recovered_text
    assert "Paragraph Three concludes the document" in recovered_text

    # Summaries and reminder extraction also succeed using the chunk fallback
    summary = summary_flow_service.get_or_create_summary(user_a.id, doc_id, force=True)
    assert summary is not None
    assert summary.summary_text


def test_empty_or_unrecoverable_documents_fail_gracefully(user_a):
    """Proves empty docs fail with ValueError and unrecoverable docs raise RuntimeError (never returning truncated preview)."""
    # 1. Empty document:
    doc_repo = DocumentRepository()
    empty_doc = doc_repo.create(user_a.id, "empty.txt", "", "txt", 0)
    doc_repo.update_status(empty_doc.id, user_a.id, "ready")

    with pytest.raises(ValueError, match="has no text content"):
        get_document_full_text(user_a.id, empty_doc.id)

    with pytest.raises(ValueError, match="has no text content"):
        summary_flow_service.get_or_create_summary(user_a.id, empty_doc.id)

    with pytest.raises(ValueError, match="has no text content"):
        reminder_flow_service.extract_events_for_document(user_a.id, empty_doc.id)

    # 2. Unrecoverable document:
    # A document with multiple chunks whose stored file AND DB chunks are deleted
    content = "Detailed sentence about long subject matter. " * 50
    doc_id = _upload_file(user_a.id, "unrecoverable.txt", content)
    doc = doc_repo.get_by_id(doc_id, user_a.id)
    assert doc is not None
    assert doc.chunk_count > 1

    # Delete stored file and text cache
    Path(doc.stored_path).unlink()
    from app.services.text_cache_service import invalidate_text_cache
    invalidate_text_cache(doc_id)

    # Delete database chunks
    ChunkRepository().delete_for_document(doc_id, user_a.id)

    # Must raise RuntimeError rather than silently returning doc.text_preview (500 chars)
    with pytest.raises(RuntimeError, match="text cannot be recovered"):
        get_document_full_text(user_a.id, doc_id)

    with pytest.raises(RuntimeError, match="text cannot be recovered"):
        summary_flow_service.get_or_create_summary(user_a.id, doc_id, force=True)

    with pytest.raises(RuntimeError, match="text cannot be recovered"):
        reminder_flow_service.extract_events_for_document(user_a.id, doc_id)


def test_user_isolation_full_text(client, user_a):
    """Proves User B cannot access User A's document text under any circumstances."""
    doc_id = _upload_file(user_a.id, "secret_usera.txt", "Top secret data for User A only.")
    doc_a = DocumentRepository().get_by_id(doc_id, user_a.id)
    assert doc_a is not None

    # Register and log in User B through the API
    reg_resp = client.post("/api/auth/register", json={"username": "userb_iso", "password": "password123"})
    assert reg_resp.status_code == 201
    user_b_id = reg_resp.json()["id"]

    login_resp = client.post("/api/auth/login", json={"username": "userb_iso", "password": "password123"})
    assert login_resp.status_code == 200
    cookies_b = dict(login_resp.cookies)

    # 1. Direct service call with wrong user_id
    with pytest.raises(ValueError, match="Document not found"):
        get_document_full_text(user_id=user_b_id, doc_id=doc_id)

    # 2. Direct service call passing User A's doc model to User B
    with pytest.raises(ValueError, match="Document not found"):
        get_document_full_text(user_id=user_b_id, doc_id=doc_id, doc=doc_a)

    # 3. Flow services with User B credentials
    with pytest.raises(ValueError, match="Document not found"):
        summary_flow_service.get_or_create_summary(user_id=user_b_id, doc_id=doc_id)

    with pytest.raises(ValueError, match="Document not found"):
        reminder_flow_service.extract_events_for_document(user_id=user_b_id, doc_id=doc_id)

    # 4. API endpoints with User B auth cookies
    resp_sum = client.post(f"/api/documents/{doc_id}/summary", json={"force": False}, cookies=cookies_b)
    assert resp_sum.status_code == 404

    resp_ev = client.post(f"/api/documents/{doc_id}/events/extract", cookies=cookies_b)
    assert resp_ev.status_code == 404
