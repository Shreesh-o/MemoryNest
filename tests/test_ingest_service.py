"""Tests for ingest_service, document_service, and auth_service.

Uses the same autouse temp-storage fixtures from conftest.py.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from app.database.repositories import DocumentRepository, ChunkRepository, UserRepository, EventRepository
from app.services import embedding_service, vector_service
from app.services.ingest_service import IngestResult, ingest_upload, process_document, cleanup_failed_document
from app.services.document_service import list_documents, get_document, delete_document, retry_extraction
from app.services.auth_service import register, authenticate


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


class TestIngestService:
    """Tests for ingest_service functions."""

    def test_ingest_upload_txt_ready(self, temp_db, temp_chroma, temp_uploads, test_user):
        """A TXT with a date through ingest_upload -> status 'ready', chunk_count > 0, event row exists."""
        txt_content = "Submission deadline: 15 October 2026. Please submit by this date."
        file_bytes = txt_content.encode("utf-8")

        result = ingest_upload(test_user.id, "deadline.txt", file_bytes)

        assert isinstance(result, IngestResult)
        assert result.status == "ready"
        assert result.doc_id is not None
        assert result.chunk_count > 0
        assert "processed" in result.message

        # Verify document exists
        doc_repo = DocumentRepository()
        doc = doc_repo.get_by_id(result.doc_id, test_user.id)
        assert doc is not None
        assert doc.status == "ready"
        assert doc.chunk_count == result.chunk_count

        # Verify at least one event was created
        ev_repo = EventRepository()
        events = ev_repo.list_for_user(test_user.id)
        assert len(events) >= 1
        found = False
        for e in events:
            if e.event_date == "2026-10-15" or "October" in (e.raw_date or ""):
                found = True
                break
        assert found, "Expected an event with date 2026-10-15 or raw_date containing 'October'"

    def test_ingest_upload_duplicate(self, temp_db, temp_chroma, temp_uploads, test_user):
        """The same file twice for one user -> second is 'duplicate'."""
        txt_content = "This is a test document for duplicate detection."
        file_bytes = txt_content.encode("utf-8")

        # First upload
        result1 = ingest_upload(test_user.id, "test.txt", file_bytes)
        assert result1.status == "ready"
        assert result1.doc_id is not None

        # Second upload (same content, same user)
        result2 = ingest_upload(test_user.id, "test.txt", file_bytes)
        assert result2.status == "duplicate"
        assert result2.doc_id == result1.doc_id
        assert "Already exists" in result2.message

    def test_ingest_upload_rejected_binary_pdf(self, temp_db, temp_chroma, temp_uploads, test_user):
        """A random binary named .pdf -> 'rejected'."""
        # Create random binary content
        file_bytes = os.urandom(512)

        result = ingest_upload(test_user.id, "corrupt.pdf", file_bytes)

        assert result.status == "rejected"
        assert result.doc_id is None
        assert result.chunk_count == 0

    def test_ingest_upload_memoryview(self, temp_db, temp_chroma, temp_uploads, test_user):
        """A memoryview as file_bytes works."""
        txt_content = "Test content for memoryview."
        file_bytes = memoryview(txt_content.encode("utf-8"))

        result = ingest_upload(test_user.id, "mv_test.txt", file_bytes)

        assert result.status == "ready"
        assert result.doc_id is not None
        assert result.chunk_count > 0

    def test_ingest_upload_bytearray(self, temp_db, temp_chroma, temp_uploads, test_user):
        """A bytearray as file_bytes works."""
        txt_content = "Test content for bytearray."
        file_bytes = bytearray(txt_content.encode("utf-8"))

        result = ingest_upload(test_user.id, "ba_test.txt", file_bytes)

        assert result.status == "ready"
        assert result.doc_id is not None
        assert result.chunk_count > 0

    def test_ingest_upload_empty_file_rejected(self, temp_db, temp_chroma, temp_uploads, test_user):
        """Empty file is rejected."""
        file_bytes = b""

        result = ingest_upload(test_user.id, "empty.txt", file_bytes)

        assert result.status == "rejected"
        assert "empty" in result.message.lower()

    def test_ingest_upload_oversized_rejected(self, temp_db, temp_chroma, temp_uploads, test_user):
        """Oversized file is rejected."""
        import app.utils.config as config_module
        max_size = config_module.MAX_FILE_SIZE_BYTES
        file_bytes = b"x" * (max_size + 1)

        result = ingest_upload(test_user.id, "large.txt", file_bytes)

        assert result.status == "rejected"
        assert "too large" in result.message.lower()

    def test_ingest_upload_invalid_extension_rejected(self, temp_db, temp_chroma, temp_uploads, test_user):
        """File with invalid extension is rejected."""
        file_bytes = b"test content"

        result = ingest_upload(test_user.id, "malware.exe", file_bytes)

        assert result.status == "rejected"
        assert "unsupported" in result.message.lower() or "not allowed" in result.message.lower()


class TestDocumentService:
    """Tests for document_service functions."""

    def test_list_documents(self, temp_db, temp_chroma, temp_uploads, test_user):
        """list_documents returns all documents for user."""
        # Create a test document
        txt_content = "Test document for listing."
        file_bytes = txt_content.encode("utf-8")
        result = ingest_upload(test_user.id, "list_test.txt", file_bytes)
        assert result.status == "ready"

        docs = list_documents(test_user.id)
        assert len(docs) >= 1
        doc_ids = [d.id for d in docs]
        assert result.doc_id in doc_ids

    def test_get_document(self, temp_db, temp_chroma, temp_uploads, test_user):
        """get_document returns specific document."""
        txt_content = "Test document for get."
        file_bytes = txt_content.encode("utf-8")
        result = ingest_upload(test_user.id, "get_test.txt", file_bytes)
        assert result.status == "ready"

        doc = get_document(test_user.id, result.doc_id)
        assert doc is not None
        assert doc.id == result.doc_id
        assert doc.filename == "get_test.txt"

        # Non-existent document
        doc = get_document(test_user.id, 99999)
        assert doc is None

    def test_delete_document(self, temp_db, temp_chroma, temp_uploads, test_user):
        """delete_document removes file, chunks, vectors, and document row."""
        txt_content = "Document to be deleted."
        file_bytes = txt_content.encode("utf-8")
        result = ingest_upload(test_user.id, "delete_test.txt", file_bytes)
        assert result.status == "ready"

        doc_id = result.doc_id
        doc_repo = DocumentRepository()
        chunk_repo = ChunkRepository()

        # Verify everything exists
        doc = doc_repo.get_by_id(doc_id, test_user.id)
        assert doc is not None
        assert doc.status == "ready"
        chunks = chunk_repo.list_for_document(doc_id, test_user.id)
        assert len(chunks) > 0

        vs = vector_service.get_vector_service()
        results = vs.query(test_user.id, embedding_service.embed_query("deleted"), top_k=5)
        doc_vectors = [r for r in results if r["metadata"].get("document_id") == doc_id]
        assert len(doc_vectors) > 0

        # Delete the document
        delete_document(test_user.id, doc_id)

        # Verify file is deleted
        assert not Path(doc.stored_path).exists()

        # Verify chunks are deleted
        chunks_after = chunk_repo.list_for_document(doc_id, test_user.id)
        assert len(chunks_after) == 0

        # Verify vectors are deleted
        results_after = vs.query(test_user.id, embedding_service.embed_query("deleted"), top_k=5)
        doc_vectors_after = [r for r in results_after if r["metadata"].get("document_id") == doc_id]
        assert len(doc_vectors_after) == 0

        # Verify document is deleted
        deleted_doc = doc_repo.get_by_id(doc_id, test_user.id)
        assert deleted_doc is None

    def test_retry_extraction_error_state(self, temp_db, temp_chroma, temp_uploads, test_user):
        """retry_extraction works for error-state documents."""
        from app.services.ingest_service import _save_file_to_disk

        # Create a document in error state manually
        txt_content = "Test content for retry."
        file_bytes = txt_content.encode("utf-8")
        stored_path, size = _save_file_to_disk(test_user.id, "retry.txt", file_bytes)

        doc_repo = DocumentRepository()
        doc = doc_repo.create(test_user.id, "retry.txt", stored_path, "txt", size, status="error")
        doc_repo.update_status(doc.id, test_user.id, "error", "test error")

        # Retry should work
        retry_extraction(test_user.id, doc.id)

        # Verify document is now ready
        updated_doc = doc_repo.get_by_id(doc.id, test_user.id)
        assert updated_doc.status == "ready"
        assert updated_doc.chunk_count > 0

    def test_retry_extraction_non_error_raises(self, temp_db, temp_chroma, temp_uploads, test_user):
        """retry_extraction raises for non-error documents."""
        txt_content = "Test content for retry."
        file_bytes = txt_content.encode("utf-8")
        result = ingest_upload(test_user.id, "retry_test.txt", file_bytes)
        assert result.status == "ready"

        with pytest.raises(ValueError, match="not in error state"):
            retry_extraction(test_user.id, result.doc_id)

    def test_retry_extraction_not_found_raises(self, temp_db, temp_chroma, temp_uploads, test_user):
        """retry_extraction raises for non-existent document."""
        with pytest.raises(ValueError, match="not found"):
            retry_extraction(test_user.id, 99999)


class TestAuthService:
    """Tests for auth_service functions."""

    def test_register_and_authenticate(self, temp_db):
        """Register then authenticate works."""
        user = register("alice", "secret123", "alice@example.com")
        assert user.username == "alice"
        assert user.email == "alice@example.com"

        logged = authenticate("alice", "secret123")
        assert logged is not None
        assert logged.id == user.id
        assert logged.username == "alice"

    def test_authenticate_wrong_password(self, temp_db):
        """Wrong password returns None."""
        register("bob", "secret123")
        logged = authenticate("bob", "wrong")
        assert logged is None

    def test_authenticate_unknown_user(self, temp_db):
        """Unknown user returns None."""
        logged = authenticate("ghost", "secret123")
        assert logged is None

    def test_register_duplicate_raises(self, temp_db):
        """Duplicate username raises ValueError."""
        register("carol", "secret123")
        with pytest.raises(ValueError, match="already taken"):
            register("carol", "other123")

    def test_register_bad_username_raises(self, temp_db):
        """Bad username raises ValueError."""
        with pytest.raises(ValueError, match="3-32"):
            register("ab", "secret123")
        with pytest.raises(ValueError, match="3-32"):
            register("bad name!", "secret123")

    def test_register_short_password_raises(self, temp_db):
        """Short password raises ValueError."""
        with pytest.raises(ValueError, match="6 characters"):
            register("dave", "123")