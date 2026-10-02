"""Tests for the repair script."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.database.repositories import DocumentRepository, ChunkRepository, UserRepository
from app.services import vector_service, embedding_service


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
        sys.executable, "scripts/repair.py", "--fix", "--yes", "--db-path", str(temp_db),
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
        sys.executable, "scripts/repair.py", "--fix", "--yes", "--db-path", str(temp_db),
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
        sys.executable, "scripts/repair.py", "--fix", "--yes", "--db-path", str(temp_db),
    ], capture_output=True, text=True, cwd="/home/shreesh/MemoryNest", env=env)
    
    # Verify orphan chunks were removed
    chunk_repo = ChunkRepository()
    chunks = chunk_repo.list_for_document(doc.id, test_user.id)
    # Document was deleted, so doc_id should not exist
    # The orphan chunks should have been cleaned up
    assert len(chunks) == 0


def test_repair_default_db_path_from_config(temp_db, temp_chroma, temp_uploads, test_user):
    """Without --db-path, repair.py uses the DB path from config (env DB_PATH)."""
    # Create a known issue: an orphan file
    orphan = temp_uploads / str(test_user.id) / "stray_default.txt"
    orphan.parent.mkdir(parents=True, exist_ok=True)
    orphan.write_text("stray file with no document row")

    env = os.environ.copy()
    assert env["DB_PATH"] == str(temp_db)  # the autouse fixture's DB
    result = subprocess.run(
        [sys.executable, "scripts/repair.py"],
        capture_output=True, text=True, cwd="/home/shreesh/MemoryNest", env=env,
    )

    # Dry run on the config default: no crash, path shown, issue found
    assert result.returncode == 1
    assert "NameError" not in result.stderr
    assert str(temp_db) in result.stdout
    assert "Orphan files: 1" in result.stdout
    assert orphan.exists()  # dry run must not delete


def test_repair_fix_refused_without_yes(temp_db, temp_chroma, temp_uploads, test_user):
    """--fix without --yes is refused (exit 2) and changes nothing."""
    orphan = temp_uploads / str(test_user.id) / "stray_no_yes.txt"
    orphan.parent.mkdir(parents=True, exist_ok=True)
    orphan.write_text("stray")

    env = os.environ.copy()
    result = subprocess.run(
        [sys.executable, "scripts/repair.py", "--fix", "--db-path", str(temp_db)],
        capture_output=True, text=True, cwd="/home/shreesh/MemoryNest", env=env,
    )

    assert result.returncode == 2
    assert "--yes" in result.stdout
    assert str(temp_db) in result.stdout  # path shown before refusing
    assert orphan.exists()  # nothing was changed


def test_repair_fix_with_yes(temp_db, temp_chroma, temp_uploads, test_user):
    """--fix --yes applies fixes and exits 0 when nothing remains."""
    orphan = temp_uploads / str(test_user.id) / "stray_yes.txt"
    orphan.parent.mkdir(parents=True, exist_ok=True)
    orphan.write_text("stray")

    env = os.environ.copy()
    result = subprocess.run(
        [sys.executable, "scripts/repair.py", "--fix", "--yes", "--db-path", str(temp_db)],
        capture_output=True, text=True, cwd="/home/shreesh/MemoryNest", env=env,
    )

    assert result.returncode == 0
    assert "Issues remaining after fix: 0" in result.stdout
    assert not orphan.exists()