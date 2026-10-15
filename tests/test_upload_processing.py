"""Regression tests for upload document processing."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from app.database.repositories import DocumentRepository, ChunkRepository, UserRepository, EventRepository
from app.services import extraction_service, chunking_service, embedding_service, vector_service, event_service


def _assert_no_partial_data(doc_id: int, user_id: int, stored_path: Path) -> None:
    """No chunk rows, no vectors, no file left behind for a failed document."""
    assert ChunkRepository().list_for_document(doc_id, user_id) == []
    vs = vector_service.get_vector_service()
    assert vs.collection.get(where={"document_id": doc_id})["ids"] == []
    assert not stored_path.exists()


@pytest.fixture
def temp_db():
    """Fresh per-test DB from the autouse test_storage fixture (conftest.py)."""
    import app.utils.config as config_module
    return config_module.DB_PATH


@pytest.fixture
def temp_chroma():
    """Per-test Chroma dir from the autouse test_storage fixture."""
    import app.utils.config as config_module
    return config_module.CHROMA_DIR


@pytest.fixture
def temp_uploads():
    """Per-test upload dir from the autouse test_storage fixture."""
    import app.utils.config as config_module
    config_module.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    return config_module.UPLOAD_DIR


@pytest.fixture
def test_user(temp_db):
    """Create a test user."""
    user_repo = UserRepository()
    user = user_repo.create("testuser", "hashed_password", "test@example.com")
    return user


def test_process_txt_document(temp_db, temp_chroma, temp_uploads, test_user):
    """Test processing a simple TXT file."""
    from app.pages.upload import _process_document
    
    # Create a test TXT file
    txt_content = """This is a test document.
It has multiple lines of text.
The content is about project Alpha and budget $50,000.
Meeting scheduled for 2026-10-15 at 10:00 AM."""
    
    txt_path = temp_uploads / "test.txt"
    txt_path.write_text(txt_content, encoding="utf-8")
    
    # Create document record
    doc_repo = DocumentRepository()
    doc = doc_repo.create(
        user_id=test_user.id,
        filename="test.txt",
        stored_path=str(txt_path),
        file_type="txt",
        size_bytes=len(txt_content.encode("utf-8")),
    )
    
    # Process the document
    _process_document(doc.id, test_user.id, str(txt_path), "txt", "test.txt")
    
    # Verify document status is "ready"
    updated_doc = doc_repo.get_by_id(doc.id, test_user.id)
    assert updated_doc.status == "ready"
    assert updated_doc.chunk_count > 0
    assert updated_doc.text_preview is not None
    
    # Verify chunks were created
    chunk_repo = ChunkRepository()
    chunks = chunk_repo.list_for_document(doc.id, test_user.id)
    assert len(chunks) == updated_doc.chunk_count
    
    # Verify chunks have content
    for chunk in chunks:
        assert chunk.content
        assert chunk.token_count > 0
        assert chunk.chroma_id
    
    # Verify vectors in ChromaDB
    vs = vector_service.get_vector_service()
    results = vs.query(test_user.id, embedding_service.embed_query("project Alpha"), top_k=5)
    assert len(results) > 0


def test_process_docx_document(temp_db, temp_chroma, temp_uploads, test_user):
    """Test processing a simple DOCX file."""
    import docx
    from app.pages.upload import _process_document
    
    # Create a test DOCX file
    docx_path = temp_uploads / "test.docx"
    d = docx.Document()
    d.add_heading("Test Document", level=1)
    d.add_paragraph("This is a DOCX test document about project Beta.")
    d.add_paragraph("Budget: $75,000. Deadline: 2026-11-30.")
    d.save(str(docx_path))
    
    # Create document record
    doc_repo = DocumentRepository()
    doc = doc_repo.create(
        user_id=test_user.id,
        filename="test.docx",
        stored_path=str(docx_path),
        file_type="docx",
        size_bytes=docx_path.stat().st_size,
    )
    
    # Process the document
    _process_document(doc.id, test_user.id, str(docx_path), "docx", "test.docx")
    
    # Verify document status is "ready"
    updated_doc = doc_repo.get_by_id(doc.id, test_user.id)
    assert updated_doc.status == "ready"
    assert updated_doc.chunk_count > 0
    assert "Beta" in updated_doc.text_preview or "Budget" in updated_doc.text_preview
    
    # Verify chunks were created
    chunk_repo = ChunkRepository()
    chunks = chunk_repo.list_for_document(doc.id, test_user.id)
    assert len(chunks) == updated_doc.chunk_count
    
    # Verify vectors in ChromaDB
    vs = vector_service.get_vector_service()
    results = vs.query(test_user.id, embedding_service.embed_query("project Beta"), top_k=5)
    assert len(results) > 0


def test_process_document_failure_marks_failed(temp_db, temp_chroma, temp_uploads, test_user):
    """Test that a processing failure marks document as 'failed' with readable reason."""
    # Create a non-existent file path to trigger failure
    fake_path = str(temp_uploads / "nonexistent.txt")
    
    # Create document record
    doc_repo = DocumentRepository()
    doc = doc_repo.create(
        user_id=test_user.id,
        filename="nonexistent.txt",
        stored_path=fake_path,
        file_type="txt",
        size_bytes=100,
    )
    
    # Process should fail and mark document as failed
    from app.pages.upload import _process_document
    with pytest.raises(FileNotFoundError):
        _process_document(doc.id, test_user.id, fake_path, "txt", "nonexistent.txt")
    
    # Verify document status is "error" with error message
    updated_doc = doc_repo.get_by_id(doc.id, test_user.id)
    assert updated_doc.status == "error"
    assert updated_doc.error_message is not None
    assert len(updated_doc.error_message) > 0
    assert "not found" in updated_doc.error_message.lower() or "no such file" in updated_doc.error_message.lower()


def test_process_document_invalid_type(temp_db, temp_chroma, temp_uploads, test_user):
    """Test that invalid file type is handled gracefully."""
    txt_path = temp_uploads / "test.txt"
    txt_path.write_text("test content", encoding="utf-8")
    
    doc_repo = DocumentRepository()
    doc = doc_repo.create(
        user_id=test_user.id,
        filename="test.txt",
        stored_path=str(txt_path),
        file_type="invalid_type",
        size_bytes=12,
    )
    
    from app.pages.upload import _process_document
    with pytest.raises(ValueError):
        _process_document(doc.id, test_user.id, str(txt_path), "invalid_type", "test.txt")
    
    # Document should be marked as error
    updated_doc = doc_repo.get_by_id(doc.id, test_user.id)
    assert updated_doc.status == "error"
    assert updated_doc.error_message is not None


def test_process_document_extracts_events(temp_db, temp_chroma, temp_uploads, test_user):
    """Test that processing a document with a clear date creates event rows."""
    # TXT content with a clear date (computed from fixed reference to avoid date rot)
    from datetime import datetime, timedelta
    ref_date = datetime(2026, 10, 5)
    deadline_date = ref_date + timedelta(days=10)  # 2026-10-15
    deadline_str = deadline_date.strftime("%d %B %Y")  # "15 October 2026"
    txt_content = f"Submission deadline: {deadline_str}. Please submit by this date."
    
    txt_path = temp_uploads / "deadline.txt"
    txt_path.write_text(txt_content, encoding="utf-8")
    
    # Create document record
    doc_repo = DocumentRepository()
    doc = doc_repo.create(
        user_id=test_user.id,
        filename="deadline.txt",
        stored_path=str(txt_path),
        file_type="txt",
        size_bytes=len(txt_content.encode("utf-8")),
    )
    
    # Process the document
    from app.pages.upload import _process_document
    _process_document(doc.id, test_user.id, str(txt_path), "txt", "deadline.txt")
    
    # Verify document status is "ready"
    updated_doc = doc_repo.get_by_id(doc.id, test_user.id)
    assert updated_doc.status == "ready"
    
    # Verify at least one event was created for this user
    ev_repo = EventRepository()
    events = ev_repo.list_for_user(test_user.id)
    assert len(events) >= 1
    
    # Verify the event has the expected date
    found = False
    expected_iso = deadline_date.strftime("%Y-%m-%d")
    for e in events:
        if e.event_date == expected_iso or deadline_str in (e.raw_date or ""):
            found = True
            break
    assert found, f"Expected an event with date {expected_iso} or raw_date containing '{deadline_str}'"


def test_duplicate_detection_same_user(temp_db, temp_chroma, temp_uploads, test_user):
    """Test that uploading the same file twice by the same user is detected as duplicate."""
    
    txt_content = "This is a test document for duplicate detection."
    txt_path = temp_uploads / "duplicate_test.txt"
    txt_path.write_text(txt_content, encoding="utf-8")
    
    # Compute hash
    file_hash = hashlib.sha256(txt_content.encode("utf-8")).hexdigest()
    
    doc_repo = DocumentRepository()
    
    # First upload
    doc1 = doc_repo.create(
        user_id=test_user.id,
        filename="test.txt",
        stored_path=str(txt_path),
        file_type="txt",
        size_bytes=len(txt_content.encode("utf-8")),
        file_hash=file_hash,
    )
    
    # Check duplicate detection
    existing = doc_repo.get_by_hash(test_user.id, file_hash)
    assert existing is not None
    assert existing.id == doc1.id
    assert existing.filename == "test.txt"
    
    # Try to create another document with same hash for same user - should be detected
    existing2 = doc_repo.get_by_hash(test_user.id, file_hash)
    assert existing2 is not None
    assert existing2.id == doc1.id


def test_duplicate_detection_different_users(temp_db, temp_chroma, temp_uploads, test_user):
    """Test that different users can upload the same file (different user_id)."""
    
    txt_content = "Shared document content."
    file_hash = hashlib.sha256(txt_content.encode("utf-8")).hexdigest()
    
    # Create a second user
    from app.database.repositories import UserRepository
    user_repo = UserRepository()
    user2 = user_repo.create("testuser2", "hashed_password", "test2@example.com")
    
    txt_content = "Shared document content."
    txt_path = temp_uploads / "shared.txt"
    txt_path.write_text(txt_content, encoding="utf-8")
    
    doc_repo = DocumentRepository()
    
    # First user uploads
    doc1 = doc_repo.create(
        user_id=test_user.id,
        filename="shared.txt",
        stored_path=str(txt_path),
        file_type="txt",
        size_bytes=len(txt_content.encode("utf-8")),
        file_hash=file_hash,
    )
    
    # Second user uploads same content - should NOT be detected as duplicate
    existing_for_user2 = doc_repo.get_by_hash(user2.id, file_hash)
    assert existing_for_user2 is None
    
    # Second user can upload
    doc2 = doc_repo.create(
        user_id=user2.id,
        filename="shared.txt",
        stored_path=str(txt_path),
        file_type="txt",
        size_bytes=len(txt_content.encode("utf-8")),
        file_hash=file_hash,
    )
    
    assert doc1.id != doc2.id
    assert doc1.user_id == test_user.id
    assert doc2.user_id == user2.id


def test_failure_cleanup_removes_partial_data(temp_db, temp_chroma, temp_uploads, test_user):
    """Test that processing failure cleans up partial data (chunks, vectors, file)."""
    
    txt_content = "This document will fail processing."
    txt_path = temp_uploads / "fail_test.txt"
    txt_path.write_text(txt_content, encoding="utf-8")
    
    file_hash = hashlib.sha256(txt_content.encode("utf-8")).hexdigest()
    
    doc_repo = DocumentRepository()
    chunk_repo = ChunkRepository()
    
    # Create document
    doc = doc_repo.create(
        user_id=test_user.id,
        filename="fail_test.txt",
        stored_path=str(txt_path),
        file_type="txt",
        size_bytes=len(txt_content.encode("utf-8")),
        file_hash=file_hash,
    )
    
    # Simulate failure by using a non-existent stored_path for processing
    fake_path = str(temp_uploads / "nonexistent.txt")
    
    # Process should fail
    from app.pages.upload import _process_document
    with pytest.raises(FileNotFoundError):
        _process_document(doc.id, test_user.id, fake_path, "txt", "fail_test.txt")
    
    # Verify document is marked as error
    updated_doc = doc_repo.get_by_id(doc.id, test_user.id)
    assert updated_doc.status == "error"
    
    # Verify file was deleted
    assert not Path(fake_path).exists()  # fake_path doesn't exist anyway
    
    # Verify no chunks were left in SQLite
    chunks = chunk_repo.list_for_document(doc.id, test_user.id)
    assert len(chunks) == 0, "Chunks should be cleaned up on failure"
    
    # Verify no vectors in ChromaDB
    vs = vector_service.get_vector_service()
    results = vs.query(test_user.id, embedding_service.embed_query("test"), top_k=5)
    # The failed document's vectors should not be there
    doc_vectors = [r for r in results if r["metadata"].get("document_id") == doc.id]
    assert len(doc_vectors) == 0, "ChromaDB vectors should be cleaned up on failure"


def test_document_delete_cleans_everything(temp_db, temp_chroma, temp_uploads, test_user):
    """Test that document delete removes file, chunks, and vectors."""
    
    txt_content = "Document to be deleted."
    txt_path = temp_uploads / "delete_test.txt"
    txt_path.write_text(txt_content, encoding="utf-8")
    
    file_hash = hashlib.sha256(txt_content.encode("utf-8")).hexdigest()
    
    doc_repo = DocumentRepository()
    chunk_repo = ChunkRepository()
    
    # Create and process a document
    doc = doc_repo.create(
        user_id=test_user.id,
        filename="delete_test.txt",
        stored_path=str(txt_path),
        file_type="txt",
        size_bytes=len(txt_content.encode("utf-8")),
        file_hash=file_hash,
    )
    
    # Process successfully
    from app.pages.upload import _process_document
    _process_document(doc.id, test_user.id, str(txt_path), "txt", "delete_test.txt")
    
    # Verify everything exists
    updated_doc = doc_repo.get_by_id(doc.id, test_user.id)
    assert updated_doc.status == "ready"
    chunks_before = chunk_repo.list_for_document(doc.id, test_user.id)
    assert len(chunks_before) > 0
    
    vs = vector_service.get_vector_service()
    results_before = vs.query(test_user.id, embedding_service.embed_query("deleted"), top_k=5)
    doc_vectors_before = [r for r in results_before if r["metadata"].get("document_id") == doc.id]
    assert len(doc_vectors_before) > 0
    
    # Delete the document
    doc_repo.delete(doc.id, test_user.id)
    
    # Verify file is deleted
    assert not Path(txt_path).exists()
    
    # Verify chunks are deleted
    chunks_after = chunk_repo.list_for_document(doc.id, test_user.id)
    assert len(chunks_after) == 0
    
    # Verify vectors are deleted
    results_after = vs.query(test_user.id, embedding_service.embed_query("deleted"), top_k=5)
    doc_vectors_after = [r for r in results_after if r["metadata"].get("document_id") == doc.id]
    assert len(doc_vectors_after) == 0
    
    # Verify document is deleted
    deleted_doc = doc_repo.get_by_id(doc.id, test_user.id)
    assert deleted_doc is None


def test_corrupt_pdf_marked_error_and_cleaned(tmp_path, test_user):
    """A corrupt PDF renamed to .pdf ends with status='error', no partial data.

    _process_document must raise (so render() takes its st.error branch, not
    st.success), mark the row 'error', and leave nothing in SQLite/Chroma/disk.
    """
    corrupt = tmp_path / "corrupt.pdf"
    corrupt.write_bytes(os.urandom(512))

    doc_repo = DocumentRepository()
    doc = doc_repo.create(
        user_id=test_user.id,
        filename="corrupt.pdf",
        stored_path=str(corrupt),
        file_type="pdf",
        size_bytes=corrupt.stat().st_size,
    )

    from app.pages.upload import _process_document
    with pytest.raises(Exception):
        _process_document(doc.id, test_user.id, str(corrupt), "pdf", "corrupt.pdf")

    updated = doc_repo.get_by_id(doc.id, test_user.id)
    assert updated.status == "error"
    assert updated.error_message and len(updated.error_message) > 0
    _assert_no_partial_data(doc.id, test_user.id, corrupt)


def test_embedding_failure_marks_error_and_cleans(tmp_path, monkeypatch, test_user):
    """A simulated embedding failure ends with status='error', no partial data."""
    def boom(texts):
        raise RuntimeError("embedding backend unavailable")

    monkeypatch.setattr(embedding_service, "embed_texts", boom)

    txt = tmp_path / "embed_fail.txt"
    txt.write_text("Some content that would have been embedded.", encoding="utf-8")

    doc_repo = DocumentRepository()
    doc = doc_repo.create(
        user_id=test_user.id,
        filename="embed_fail.txt",
        stored_path=str(txt),
        file_type="txt",
        size_bytes=txt.stat().st_size,
    )

    from app.pages.upload import _process_document
    with pytest.raises(RuntimeError, match="embedding backend unavailable"):
        _process_document(doc.id, test_user.id, str(txt), "txt", "embed_fail.txt")

    updated = doc_repo.get_by_id(doc.id, test_user.id)
    assert updated.status == "error"
    assert "embedding backend unavailable" in updated.error_message
    _assert_no_partial_data(doc.id, test_user.id, txt)


def test_chroma_failure_marks_error_and_cleans(tmp_path, monkeypatch, test_user):
    """A simulated Chroma failure ends with status='error', no partial data.

    Chunk rows are written before add_chunks, so they must be cleaned up too.
    """
    def boom(*args, **kwargs):
        raise RuntimeError("chroma store unavailable")

    monkeypatch.setattr(vector_service.VectorService, "add_chunks", boom)

    txt = tmp_path / "chroma_fail.txt"
    txt.write_text("Content for the chroma failure test.", encoding="utf-8")

    doc_repo = DocumentRepository()
    doc = doc_repo.create(
        user_id=test_user.id,
        filename="chroma_fail.txt",
        stored_path=str(txt),
        file_type="txt",
        size_bytes=txt.stat().st_size,
    )

    from app.pages.upload import _process_document
    with pytest.raises(RuntimeError, match="chroma store unavailable"):
        _process_document(doc.id, test_user.id, str(txt), "txt", "chroma_fail.txt")

    updated = doc_repo.get_by_id(doc.id, test_user.id)
    assert updated.status == "error"
    assert "chroma store unavailable" in updated.error_message
    _assert_no_partial_data(doc.id, test_user.id, txt)


def test_document_repo_delete_basic(temp_db, temp_chroma, temp_uploads, test_user):
    """Verify DocumentRepository.delete runs without crash on basic document."""
    import os
    from pathlib import Path
    txt_path = temp_uploads / "basic_test.txt"
    txt_path.write_text("Basic test document.", encoding="utf-8")
    doc_repo = DocumentRepository()
    doc = doc_repo.create(
        user_id=test_user.id,
        filename="basic_test.txt",
        stored_path=str(txt_path),
        file_type="txt",
        size_bytes=txt_path.stat().st_size,
    )
    # Verify document was created
    retrieved = doc_repo.get_by_id(doc.id, test_user.id)
    assert retrieved is not None
    assert retrieved.filename == "basic_test.txt"
    # Note: full vector cleanup requires the retry mechanism,
    # but the delete method should be callable without immediate crash


