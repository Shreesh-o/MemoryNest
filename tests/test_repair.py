"""Tests for the repair script."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.database.database import init_db
from app.database.repositories import DocumentRepository, ChunkRepository, UserRepository
from app.services import vector_service, embedding_service


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
    from app.services import vector_service
    vector_service.VectorService._instance = None
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


def test_repair_orphan_vectors(temp_db, temp_chroma, temp_uploads, test_user):
    """Test repair script detects and fixes orphan ChromaDB vectors."""
    import hashlib
    
    # Create a document and process it
    txt_content = "Test document for orphan vector test."
    txt_path = temp_uploads / "orphan_test.txt"
    txt_path.write_text(txt_content, encoding="utf-8")
    
    file_hash = hashlib.sha256(txt_content.encode("utf-8")).hexdigest()
    
    doc_repo = DocumentRepository()
    doc = doc_repo.create(
        user_id=test_user.id,
        filename="orphan_test.txt",
        stored_path=str(txt_path),
        file_type="txt",
        size_bytes=len(txt_content.encode("utf-8")),
        file_hash=file_hash,
    )
    
    from app.pages.upload import _process_document
    _process_document(doc.id, test_user.id, str(txt_path), "txt", "orphan_test.txt")
    
    # Manually add an orphan vector to ChromaDB
    vs = vector_service.get_vector_service()
    fake_embedding = embedding_service.embed_query("fake orphan vector")
    vs.add_chunks(
        user_id=test_user.id,
        document_id=99999,  # non-existent document
        filename="fake.txt",
        chunks=[{
            "index": 0,
            "text": "fake orphan vector",
            "token_count": 10,
            "chroma_id": "fake-orphan-chroma-id",
            "embedding": fake_embedding,
        }]
    )
    
    # Run repair dry run
    env = os.environ.copy()
    env["UPLOAD_DIR"] = str(temp_uploads)
    env["CHROMA_DIR"] = str(temp_chroma)
    result = subprocess.run([
        sys.executable, "scripts/repair.py", "--db-path", str(temp_db),
    ], capture_output=True, text=True, cwd="/home/shreesh/MemoryNest", env=env)
    
    assert "orphan" in result.stdout.lower()
    
    # Run repair with fix
    result = subprocess.run([
        sys.executable, "scripts/repair.py", "--fix", "--db-path", str(temp_db),
    ], capture_output=True, text=True, cwd="/home/shreesh/MemoryNest", env=env)
    
    # Verify orphan vector was removed
    vs = vector_service.get_vector_service()
    results = vs.collection.get(ids=["fake-orphan-chroma-id"])
    assert len(results["ids"]) == 0


def test_repair_orphan_files(temp_db, temp_chroma, temp_uploads, test_user):
    """Test repair script detects and fixes orphan uploaded files."""
    import hashlib
    
    # Create an orphan file (file in uploads but no document in DB)
    orphan_file = temp_uploads / str(test_user.id) / "orphan_file.txt"
    orphan_file.parent.mkdir(parents=True, exist_ok=True)
    orphan_file.write_text("This file has no database record.")
    
    # Run repair dry run
    env = os.environ.copy()
    env["UPLOAD_DIR"] = str(temp_uploads)
    env["CHROMA_DIR"] = str(temp_chroma)
    result = subprocess.run([
        sys.executable, "scripts/repair.py", "--db-path", str(temp_db),
    ], capture_output=True, text=True, cwd="/home/shreesh/MemoryNest", env=env)
    
    assert "orphan" in result.stdout.lower()
    
    # Run repair with fix
    result = subprocess.run([
        sys.executable, "scripts/repair.py", "--fix", "--db-path", str(temp_db),
    ], capture_output=True, text=True, cwd="/home/shreesh/MemoryNest", env=env)
    
    # Verify orphan file was removed
    assert not orphan_file.exists()


def test_repair_chunks_without_document(temp_db, temp_chroma, temp_uploads, test_user):
    """Test repair script detects and fixes chunks without document."""
    import hashlib
    from app.database.repositories import ChunkRepository
    from app.database.repositories import DocumentRepository
    
    # Create a document and process it
    txt_content = "Test document for chunk test."
    txt_path = temp_uploads / "chunk_test.txt"
    txt_path.write_text(txt_content, encoding="utf-8")
    
    file_hash = hashlib.sha256(txt_content.encode("utf-8")).hexdigest()
    
    doc_repo = DocumentRepository()
    doc = doc_repo.create(
        user_id=test_user.id,
        filename="chunk_test.txt",
        stored_path=str(txt_path),
        file_type="txt",
        size_bytes=len(txt_content.encode("utf-8")),
        file_hash=file_hash,
    )
    
    # Process document
    from app.pages.upload import _process_document
    _process_document(doc.id, test_user.id, str(txt_path), "txt", "chunk_test.txt")
    
    # Manually delete the document but leave chunks (simulate orphan chunks)
    doc_repo.delete(doc.id, test_user.id)
    
    # Run repair dry run
    env = os.environ.copy()
    env["UPLOAD_DIR"] = str(temp_uploads)
    env["CHROMA_DIR"] = str(temp_chroma)
    result = subprocess.run([
        sys.executable, "scripts/repair.py", "--db-path", str(temp_db),
    ], capture_output=True, text=True, cwd="/home/shreesh/MemoryNest", env=env)
    
    assert "chunk" in result.stdout.lower()
    
    # Run repair with fix
    result = subprocess.run([
        sys.executable, "scripts/repair.py", "--fix", "--db-path", str(temp_db),
    ], capture_output=True, text=True, cwd="/home/shreesh/MemoryNest", env=env)
    
    # Verify orphan chunks were removed
    chunk_repo = ChunkRepository()
    chunks = chunk_repo.list_for_document(doc.id, test_user.id)
    # Document was deleted, so doc_id should not exist
    # The orphan chunks should have been cleaned up
    assert len(chunks) == 0