"""Tests for ARC-06: SQLite concurrency, WAL journal mode, busy timeouts, and batch operations."""

from __future__ import annotations

import concurrent.futures
import sqlite3
from pathlib import Path

import pytest

from app.database.database import get_connection, init_db
from app.database.repositories import ChunkRepository, DocumentRepository, UserRepository


def test_wal_journal_mode_enabled_on_init(tmp_path):
    """Verifies that init_db enables WAL journal mode in the database header."""
    db_path = tmp_path / "wal_test.db"
    init_db(db_path)

    conn = get_connection(db_path)
    try:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode.lower() == "wal"
    finally:
        conn.close()


def test_busy_timeout_and_foreign_keys_configured(tmp_path):
    """Verifies that get_connection sets busy_timeout to 30000ms and foreign_keys = ON."""
    db_path = tmp_path / "pragma_test.db"
    init_db(db_path)

    conn = get_connection(db_path)
    try:
        fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        assert fk == 1

        timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]
        assert timeout == 30000
    finally:
        conn.close()


def test_chunk_repository_create_batch_success():
    """Verifies atomic batch insertion of chunks in a single transaction."""
    user_repo = UserRepository()
    user = user_repo.create("batch_user", "pw_hash", "batch@example.com")

    doc_repo = DocumentRepository()
    doc = doc_repo.create(user.id, "batch.txt", "/tmp/batch.txt", "txt", 100)

    chunk_repo = ChunkRepository()
    chunks_data = [
        {
            "document_id": doc.id,
            "user_id": user.id,
            "chunk_index": i,
            "content": f"Chunk content number {i}",
            "token_count": 10 + i,
            "chroma_id": f"chroma-{doc.id}-{i}",
        }
        for i in range(15)
    ]

    created = chunk_repo.create_batch(chunks_data)
    assert len(created) == 15
    assert [c.chunk_index for c in created] == list(range(15))

    # Verify query returns all 15 chunks
    listed = chunk_repo.list_for_document(doc.id, user.id)
    assert len(listed) == 15
    assert listed[0].content == "Chunk content number 0"
    assert listed[14].content == "Chunk content number 14"


def test_chunk_repository_create_batch_rollback_on_failure():
    """Verifies that a batch failure rolls back all chunks and leaves no partial rows."""
    user_repo = UserRepository()
    user = user_repo.create("rollback_user", "pw_hash", "rb@example.com")

    doc_repo = DocumentRepository()
    doc = doc_repo.create(user.id, "rollback.txt", "/tmp/rb.txt", "txt", 100)

    chunk_repo = ChunkRepository()
    # Chunk 3 violates the foreign key / NOT NULL constraint on user_id
    chunks_data = [
        {
            "document_id": doc.id,
            "user_id": user.id,
            "chunk_index": 0,
            "content": "Valid chunk 0",
            "token_count": 10,
            "chroma_id": "c-0",
        },
        {
            "document_id": doc.id,
            "user_id": user.id,
            "chunk_index": 1,
            "content": "Valid chunk 1",
            "token_count": 10,
            "chroma_id": "c-1",
        },
        {
            "document_id": doc.id,
            "user_id": None,  # NOT NULL constraint violation
            "chunk_index": 2,
            "content": "Invalid chunk",
            "token_count": 10,
            "chroma_id": "c-2",
        },
    ]

    with pytest.raises(Exception):
        chunk_repo.create_batch(chunks_data)

    # Entire batch must be rolled back: 0 chunks in database
    assert chunk_repo.list_for_document(doc.id, user.id) == []


def test_concurrent_reads_and_writes_under_wal(tmp_path):
    """Verifies that WAL mode allows readers to execute concurrently with writers without locking."""
    db_path = tmp_path / "wal_concurrency.db"
    init_db(db_path)

    # Insert initial user
    conn = get_connection(db_path)
    conn.execute("INSERT INTO users (username, password_hash) VALUES ('init_user', 'pw')")
    conn.commit()
    conn.close()

    def _reader():
        c = get_connection(db_path)
        try:
            for _ in range(20):
                row = c.execute("SELECT COUNT(*) FROM users").fetchone()
                assert row[0] >= 1
        finally:
            c.close()
        return True

    def _writer():
        c = get_connection(db_path)
        try:
            for i in range(10):
                c.execute(f"INSERT INTO users (username, password_hash) VALUES ('user_{i}', 'pw')")
                c.commit()
        finally:
            c.close()
        return True

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        f_write = executor.submit(_writer)
        f_reads = [executor.submit(_reader) for _ in range(3)]

        assert f_write.result() is True
        for f in f_reads:
            assert f.result() is True
