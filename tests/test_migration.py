"""Tests for database migration (file_hash column addition)."""

from __future__ import annotations

import os
import tempfile
import pathlib
import sqlite3
import sys

import pytest

sys.path.insert(0, "/home/shreesh/MemoryNest")


def create_old_schema_db(db_path: pathlib.Path) -> None:
    """Create a database with the old schema (no file_hash column)."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")

    # Old users table
    conn.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    # Old documents table WITHOUT file_hash
    conn.execute("""
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            filename TEXT NOT NULL,
            stored_path TEXT NOT NULL,
            file_type TEXT NOT NULL,
            size_bytes INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'uploaded',
            error_message TEXT,
            text_preview TEXT,
            chunk_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    conn.execute("""
        CREATE TABLE document_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            token_count INTEGER NOT NULL DEFAULT 0,
            chroma_id TEXT NOT NULL UNIQUE,
            UNIQUE (document_id, chunk_index)
        )
    """)

    conn.commit()
    conn.close()


def test_migration_adds_file_hash_column():
    """Test that init_db adds file_hash column to old database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = pathlib.Path(tmpdir) / "old.db"
        create_old_schema_db(db_path)

        # Insert test data
        conn = sqlite3.connect(str(db_path))
        conn.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", ("testuser", "hash"))
        conn.execute(
            "INSERT INTO documents (user_id, filename, stored_path, file_type, size_bytes, status) VALUES (?, ?, ?, ?, ?, ?)",
            (1, "test.txt", "/tmp/test.txt", "txt", 100, "ready"),
        )
        conn.commit()
        conn.close()

        # Run migration via init_db (pass db_path directly)
        from app.database.database import init_db
        init_db(db_path)

        # Verify migration
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row

        # Check column exists
        cursor = conn.execute("PRAGMA table_info(documents)")
        columns = [row["name"] for row in cursor.fetchall()]
        assert "file_hash" in columns, "file_hash column missing after migration"

        # Check index exists
        cursor = conn.execute(
            'SELECT name FROM sqlite_master WHERE type="index" AND name="idx_documents_user_hash"'
        )
        idx = cursor.fetchone()
        assert idx is not None, "Index idx_documents_user_hash not created"

        # Check old data preserved
        cursor = conn.execute("SELECT * FROM documents")
        doc = cursor.fetchone()
        assert doc is not None, "Old document lost during migration"
        assert doc["file_hash"] == "", "Old document should have empty file_hash"

        # Check index includes file_hash
        cursor = conn.execute("PRAGMA index_info(idx_documents_user_hash)")
        idx_info = cursor.fetchall()
        assert len(idx_info) == 2, "Index should have 2 columns"
        assert idx_info[0]["name"] == "user_id"
        assert idx_info[1]["name"] == "file_hash"

        conn.close()


def test_init_db_idempotent_on_migrated_db():
    """Test that running init_db twice on migrated database is safe."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = pathlib.Path(tmpdir) / "old.db"
        create_old_schema_db(db_path)

        conn = sqlite3.connect(str(db_path))
        conn.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", ("testuser", "hash"))
        conn.execute(
            "INSERT INTO documents (user_id, filename, stored_path, file_type, size_bytes, status) VALUES (?, ?, ?, ?, ?, ?)",
            (1, "test.txt", "/tmp/test.txt", "txt", 100, "ready"),
        )
        conn.commit()
        conn.close()

        from app.database.database import init_db

        # First run
        init_db(db_path)
        # Second run should not fail
        init_db(db_path)

        # Verify state
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row

        cursor = conn.execute("PRAGMA table_info(documents)")
        columns = [row["name"] for row in cursor.fetchall()]
        assert "file_hash" in columns

        cursor = conn.execute(
            'SELECT name FROM sqlite_master WHERE type="index" AND name="idx_documents_user_hash"'
        )
        idx = cursor.fetchone()
        assert idx is not None

        conn.close()


def test_init_db_on_fresh_database():
    """Test that init_db works correctly on a brand new empty database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = pathlib.Path(tmpdir) / "fresh.db"

        from app.database.database import init_db
        init_db(db_path)

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row

        # Check all tables exist
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row["name"] for row in cursor.fetchall()}
        expected_tables = {
            "users",
            "documents",
            "document_chunks",
            "conversations",
            "messages",
            "summaries",
            "events",
            "reminders",
            "notification_logs",
        }
        assert expected_tables.issubset(tables), f"Missing tables: {expected_tables - tables}"

        # Check documents has file_hash
        cursor = conn.execute("PRAGMA table_info(documents)")
        columns = [row["name"] for row in cursor.fetchall()]
        assert "file_hash" in columns

        # Check index exists
        cursor = conn.execute(
            'SELECT name FROM sqlite_master WHERE type="index" AND name="idx_documents_user_hash"'
        )
        idx = cursor.fetchone()
        assert idx is not None

        conn.close()


def test_migration_preserves_existing_data():
    """Test that migration preserves all existing document data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = pathlib.Path(tmpdir) / "old.db"
        create_old_schema_db(db_path)

        conn = sqlite3.connect(str(db_path))
        conn.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", ("user1", "hash1"))
        conn.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", ("user2", "hash2"))
        conn.execute(
            "INSERT INTO documents (user_id, filename, stored_path, file_type, size_bytes, status, text_preview, chunk_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (1, "doc1.txt", "/path/doc1.txt", "txt", 100, "ready", "preview1", 5),
        )
        conn.execute(
            "INSERT INTO documents (user_id, filename, stored_path, file_type, size_bytes, status, text_preview, chunk_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (2, "doc2.txt", "/path/doc2.txt", "pdf", 200, "ready", "preview2", 10),
        )
        conn.commit()
        conn.close()

        from app.database.database import init_db
        init_db(db_path)

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row

        # Check both documents preserved
        cursor = conn.execute("SELECT * FROM documents ORDER BY id")
        docs = cursor.fetchall()
        assert len(docs) == 2

        doc1 = docs[0]
        assert doc1["filename"] == "doc1.txt"
        assert doc1["user_id"] == 1
        assert doc1["size_bytes"] == 100
        assert doc1["status"] == "ready"
        assert doc1["text_preview"] == "preview1"
        assert doc1["chunk_count"] == 5
        assert doc1["file_hash"] == ""

        doc2 = docs[1]
        assert doc2["filename"] == "doc2.txt"
        assert doc2["user_id"] == 2
        assert doc2["size_bytes"] == 200
        assert doc2["status"] == "ready"
        assert doc2["text_preview"] == "preview2"
        assert doc2["chunk_count"] == 10
        assert doc2["file_hash"] == ""

        conn.close()


def create_old_schema_db(db_path: pathlib.Path) -> None:
    """Create a database with the old schema (no file_hash column)."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")

    # Old users table
    conn.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    # Old documents table WITHOUT file_hash
    conn.execute("""
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            filename TEXT NOT NULL,
            stored_path TEXT NOT NULL,
            file_type TEXT NOT NULL,
            size_bytes INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'uploaded',
            error_message TEXT,
            text_preview TEXT,
            chunk_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    conn.execute("""
        CREATE TABLE document_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            token_count INTEGER NOT NULL DEFAULT 0,
            chroma_id TEXT NOT NULL UNIQUE,
            UNIQUE (document_id, chunk_index)
        )
    """)

    conn.commit()
    conn.close()


def test_fresh_vs_migrated_db_equal(tmp_path):
    """Assert that init_db on a fresh DB yields the same tables/indexes as
    migrating an old-schema DB, confirming the SCHEMA + migration are consistent."""
    import sqlite3
    import pathlib

    # 1. Fresh DB: run init_db on a new empty path (starting with old schema)
    fresh_db = pathlib.Path(str(tmp_path) / "fresh.db")
    create_old_schema_db(fresh_db)  # start with old schema (no file_hash)
    from app.database.database import init_db
    init_db(fresh_db)

    # Capture tables and indexes from fresh DB
    fresh_conn = sqlite3.connect(str(fresh_db))
    fresh_tables = set(row[0] for row in fresh_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence'"
    ).fetchall())
    fresh_indexes = set(row[0] for row in fresh_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index'"
    ).fetchall())
    fresh_conn.close()

    # 2. Migrated DB: create old-schema DB and run init_db
    migrated_db = pathlib.Path(str(tmp_path) / "migrated.db")
    create_old_schema_db(migrated_db)
    from app.database.database import init_db
    init_db(migrated_db)

    # Capture tables and indexes from migrated DB
    migrated_conn = sqlite3.connect(str(migrated_db))
    migrated_tables = set(row[0] for row in migrated_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence'"
    ).fetchall())
    migrated_indexes = set(row[0] for row in migrated_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index'"
    ).fetchall())
    migrated_conn.close()

    # 3. Assert equality
    assert fresh_tables == migrated_tables, (
        f"Tables mismatch: fresh={fresh_tables}, migrated={migrated_tables}"
    )
    assert fresh_indexes == migrated_indexes, (
        f"Indexes mismatch: fresh={fresh_indexes}, migrated={migrated_indexes}"
    )



def test_fresh_vs_migrated_db_equal(tmp_path):
    """Assert that init_db on a fresh DB yields the same tables/indexes as
    migrating an old-schema DB, confirming the SCHEMA + migration are consistent."""
    import sqlite3
    import pathlib

    # 1. Fresh DB: run init_db on a new empty path (starting with old schema)
    fresh_db = tmp_path / "fresh.db"
    create_old_schema_db(fresh_db)  # start with old schema (no file_hash)
    from app.database.database import init_db
    init_db(fresh_db)

    # Capture tables and indexes from fresh DB
    fresh_conn = sqlite3.connect(str(fresh_db))
    fresh_tables = set(row[0] for row in fresh_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence'"
    ).fetchall())
    fresh_indexes = set(row[0] for row in fresh_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index'"
    ).fetchall())
    fresh_conn.close()

    # 2. Migrated DB: create old-schema DB and run init_db
    migrated_db = tmp_path / "migrated.db"
    create_old_schema_db(migrated_db)
    from app.database.database import init_db
    init_db(migrated_db)

    # Capture tables and indexes from migrated DB
    migrated_conn = sqlite3.connect(str(migrated_db))
    migrated_tables = set(row[0] for row in migrated_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence'"
    ).fetchall())
    migrated_indexes = set(row[0] for row in migrated_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index'"
    ).fetchall())
    migrated_conn.close()

    # 3. Assert equality
    assert fresh_tables == migrated_tables, (
        f"Tables mismatch: fresh={fresh_tables}, migrated={migrated_tables}"
    )
    assert fresh_indexes == migrated_indexes, (
        f"Indexes mismatch: fresh={fresh_indexes}, migrated={migrated_indexes}"
    )
