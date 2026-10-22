"""Tests for database migration (file_hash column addition)."""

from __future__ import annotations

import pathlib
import sqlite3

import pytest


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
    import tempfile
    import pathlib

    with tempfile.TemporaryDirectory() as tmp:
        db_path = pathlib.Path(tmp) / "test.db"
        create_old_schema_db(db_path)
        from app.database.database import init_db
        init_db(db_path)

        # Verify the file_hash column and index were added
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("PRAGMA table_info(documents)")
        columns = [row[1] for row in cursor.fetchall()]
        assert "file_hash" in columns
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name = 'idx_documents_user_hash'"
        )
        assert cursor.fetchone() is not None
        conn.close()


def test_init_db_idempotent_on_migrated_db():
    """Test that running init_db twice on migrated database is safe."""
    import tempfile
    import pathlib

    with tempfile.TemporaryDirectory() as tmp:
        db_path = pathlib.Path(tmp) / "test.db"
        create_old_schema_db(db_path)
        from app.database.database import init_db
        init_db(db_path)
        init_db(db_path)

        # Verify the file_hash column and index were added
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("PRAGMA table_info(documents)")
        columns = [row[1] for row in cursor.fetchall()]
        assert "file_hash" in columns
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name = 'idx_documents_user_hash'"
        )
        assert cursor.fetchone() is not None
        conn.close()


def test_init_db_on_fresh_database():
    """Test that init_db works correctly on a brand new empty database."""
    import tempfile
    import pathlib

    with tempfile.TemporaryDirectory() as tmp:
        db_path = pathlib.Path(tmp) / "test.db"
        from app.database.database import init_db
        init_db(db_path)

        # Verify basic tables exist
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = {row[0] for row in cursor}
        assert "users" in table_names
        assert "documents" in table_names
        conn.close()


def test_fresh_vs_migrated_db_equal(tmp_path):
    """Assert that init_db on a fresh DB yields the same tables/indexes as
    migrating an old-schema DB, confirming the SCHEMA + migration are consistent."""
    import sqlite3

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


def test_migration_adds_email_column_to_users():
    """Test that init_db adds email column to users table if missing."""
    import tempfile
    import pathlib

    with tempfile.TemporaryDirectory() as tmp:
        db_path = pathlib.Path(tmp) / "legacy_users.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
        conn.close()

        from app.database.database import init_db
        init_db(db_path)

        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        assert "email" in columns
        conn.close()

