"""Regression tests for upload document processing."""

from __future__ import annotations

import pytest

from app.database.database import init_db
from app.database.repositories import DocumentRepository, ChunkRepository, UserRepository
from app.pages.upload import _process_document
from app.services import extraction_service, chunking_service, embedding_service, vector_service


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test.db"
    init_db(db_path)
    monkeypatch.setattr("app.database.database.DB_PATH", db_path)
    return db_path


@pytest.fixture
def temp_chroma(tmp_path, monkeypatch):
    """Create a temporary ChromaDB directory."""
    chroma_path = tmp_path / "chroma_test"
    monkeypatch.setattr("app.services.vector_service.CHROMA_DIR", chroma_path)
    # Reset singleton properly
    from app.services import vector_service
    vector_service.VectorService._instance = None
    # Force reinitialization by removing _initialized from any existing instance
    if hasattr(vector_service.VectorService, '_initialized'):
        delattr(vector_service.VectorService, '_initialized')
    return chroma_path


@pytest.fixture
def temp_uploads(tmp_path, monkeypatch):
    """Create a temporary upload directory."""
    upload_path = tmp_path / "uploads"
    upload_path.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("app.utils.config.UPLOAD_DIR", upload_path)
    return upload_path


@pytest.fixture
def test_user(temp_db):
    """Create a test user."""
    user_repo = UserRepository()
    user = user_repo.create("testuser", "hashed_password", "test@example.com")
    return user


def test_process_txt_document(temp_db, temp_chroma, temp_uploads, test_user):
    """Test processing a simple TXT file."""
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
    
    with pytest.raises(ValueError):
        _process_document(doc.id, test_user.id, str(txt_path), "invalid_type", "test.txt")
    
    # Document should be marked as error
    updated_doc = doc_repo.get_by_id(doc.id, test_user.id)
    assert updated_doc.status == "error"
    assert updated_doc.error_message is not None