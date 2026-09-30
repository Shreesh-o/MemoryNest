"""SQLite connection handling and schema initialization."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.utils.config import DB_PATH, ensure_dirs

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    email TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    file_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL DEFAULT 0,
    file_hash TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'uploaded',
    error_message TEXT,
    text_preview TEXT,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS document_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    token_count INTEGER NOT NULL DEFAULT 0,
    chroma_id TEXT NOT NULL UNIQUE,
    UNIQUE (document_id, chunk_index)
);

CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    sources TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    summary_text TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    document_id INTEGER REFERENCES documents(id) ON DELETE SET NULL,
    event_text TEXT NOT NULL,
    event_date TEXT,
    raw_date TEXT,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'confirmed', 'skipped')),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    remind_at TEXT NOT NULL,
    channel TEXT NOT NULL DEFAULT 'email',
    subject TEXT,
    body TEXT,
    status TEXT NOT NULL DEFAULT 'scheduled'
        CHECK (status IN ('scheduled', 'sent', 'failed', 'cancelled')),
    sent_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS notification_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    reminder_id INTEGER REFERENCES reminders(id) ON DELETE SET NULL,
    kind TEXT NOT NULL,
    success INTEGER NOT NULL,
    detail TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_documents_user ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_user_hash ON documents(user_id, file_hash);
CREATE INDEX IF NOT EXISTS idx_chunks_user ON document_chunks(user_id);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_convo ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_events_user ON events(user_id, status);
CREATE INDEX IF NOT EXISTS idx_reminders_user ON reminders(user_id, status, remind_at);
"""


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Return a connection with row access by column name and FK enforcement."""
    path = db_path or DB_PATH
    ensure_dirs()
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path | None = None) -> None:
    """Create all tables if they do not exist. Run migrations for existing databases."""
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
        _migrate_add_file_hash(conn)
    finally:
        conn.close()


def _migrate_add_file_hash(conn: sqlite3.Connection) -> None:
    """Add file_hash column to documents table if it doesn't exist (migration for existing DBs)."""
    cursor = conn.execute("PRAGMA table_info(documents)")
    columns = [row[1] for row in cursor.fetchall()]
    if "file_hash" not in columns:
        conn.execute("ALTER TABLE documents ADD COLUMN file_hash TEXT NOT NULL DEFAULT ''")
        conn.commit()
        # Backfill existing rows with computed hash from stored files
        _backfill_file_hashes(conn)


def _backfill_file_hashes(conn: sqlite3.Connection) -> None:
    """Compute SHA-256 for existing documents and update file_hash column."""
    import hashlib
    rows = conn.execute("SELECT id, stored_path FROM documents WHERE file_hash = '' OR file_hash IS NULL").fetchall()
    for row in rows:
        doc_id, stored_path = row["id"], row["stored_path"]
        from pathlib import Path
        path = Path(stored_path)
        if path.exists():
            data = path.read_bytes()
            file_hash = hashlib.sha256(data).hexdigest()
            conn.execute("UPDATE documents SET file_hash = ? WHERE id = ?", (file_hash, doc_id))
    if rows:
        conn.commit()
