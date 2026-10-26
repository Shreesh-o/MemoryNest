"""Thin data-access layer over SQLite. One repository per table."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List, Optional

from app.database.database import get_connection
from app.database.models import (
    Conversation,
    Document,
    DocumentChunk,
    DocumentLink,
    Event,
    GoogleConnection,
    Message,
    NotificationLog,
    Reminder,
    Summary,
    User,
)

logger = logging.getLogger(__name__)


class BaseRepository:
    def _connect(self):
        return get_connection()

    @staticmethod
    def _row_to_dataclass(row, cls):
        return cls(**dict(row))


class UserRepository(BaseRepository):
    def create(self, username: str, password_hash: str, email: Optional[str] = None) -> User:
        conn = self._connect()
        try:
            cur = conn.execute(
                "INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)",
                (username, password_hash, email),
            )
            conn.commit()
            return self.get_by_id(cur.lastrowid)
        finally:
            conn.close()

    def get_by_id(self, user_id: int) -> Optional[User]:
        conn = self._connect()
        try:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            return self._row_to_dataclass(row, User) if row else None
        finally:
            conn.close()

    def get_by_username(self, username: str) -> Optional[User]:
        conn = self._connect()
        try:
            row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
            return self._row_to_dataclass(row, User) if row else None
        finally:
            conn.close()

    def get_by_email(self, email: str) -> Optional[User]:
        conn = self._connect()
        try:
            row = conn.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (email.strip(),)).fetchone()
            return self._row_to_dataclass(row, User) if row else None
        finally:
            conn.close()

    def update_email(self, user_id: int, email: Optional[str]) -> Optional[User]:
        conn = self._connect()
        try:
            conn.execute("UPDATE users SET email = ? WHERE id = ?", (email, user_id))
            conn.commit()
            return self.get_by_id(user_id)
        finally:
            conn.close()

    def list_all(self) -> List[User]:
        conn = self._connect()
        try:
            rows = conn.execute("SELECT * FROM users ORDER BY id").fetchall()
            return [self._row_to_dataclass(r, User) for r in rows]
        finally:
            conn.close()

    def delete(self, user_id: int) -> None:
        conn = self._connect()
        try:
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
        finally:
            conn.close()


class DocumentRepository(BaseRepository):
    def create(
        self,
        user_id: int,
        filename: str,
        stored_path: str,
        file_type: str,
        size_bytes: int = 0,
        status: str = "uploaded",
        file_hash: str = "",
    ) -> Document:
        conn = self._connect()
        try:
            cur = conn.execute(
                """INSERT INTO documents
                   (user_id, filename, stored_path, file_type, size_bytes, status, file_hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (user_id, filename, stored_path, file_type, size_bytes, status, file_hash),
            )
            conn.commit()
            return self.get_by_id(cur.lastrowid, user_id)
        finally:
            conn.close()

    def get_by_id(self, doc_id: int, user_id: int) -> Optional[Document]:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM documents WHERE id = ? AND user_id = ?", (doc_id, user_id)
            ).fetchone()
            return self._row_to_dataclass(row, Document) if row else None
        finally:
            conn.close()

    def get_by_hash(self, user_id: int, file_hash: str) -> Optional[Document]:
        """Find a document by file_hash for the same user (duplicate detection)."""
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM documents WHERE user_id = ? AND file_hash = ?",
                (user_id, file_hash),
            ).fetchone()
            return self._row_to_dataclass(row, Document) if row else None
        finally:
            conn.close()

    def list_for_user(self, user_id: int) -> List[Document]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM documents WHERE user_id = ? ORDER BY created_at DESC, id DESC",
                (user_id,),
            ).fetchall()
            return [self._row_to_dataclass(r, Document) for r in rows]
        finally:
            conn.close()

    def get_by_ids(self, doc_ids: List[int], user_id: int) -> List[Document]:
        """Fetch documents by IDs strictly scoped to the given user_id."""
        if not doc_ids:
            return []
        conn = self._connect()
        try:
            placeholders = ",".join("?" for _ in doc_ids)
            rows = conn.execute(
                f"SELECT * FROM documents WHERE user_id = ? AND id IN ({placeholders})",
                (user_id, *doc_ids),
            ).fetchall()
            return [self._row_to_dataclass(r, Document) for r in rows]
        finally:
            conn.close()

    def list_ready_for_user(self, user_id: int) -> List[Document]:
        """List ready documents for a user, ordered by filename."""
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM documents WHERE user_id = ? AND status = 'ready' ORDER BY filename ASC, id ASC",
                (user_id,),
            ).fetchall()
            return [self._row_to_dataclass(r, Document) for r in rows]
        finally:
            conn.close()

    def update_status(
        self, doc_id: int, user_id: int, status: str, error_message: Optional[str] = None
    ) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "UPDATE documents SET status = ?, error_message = ? WHERE id = ? AND user_id = ?",
                (status, error_message, doc_id, user_id),
            )
            conn.commit()
        finally:
            conn.close()

    def set_text(self, doc_id: int, user_id: int, preview: str, chunk_count: int) -> None:
        conn = self._connect()
        try:
            logger.debug("set_text: doc_id=%s, user_id=%s, preview=%r, chunk_count=%s", doc_id, user_id, preview, chunk_count)
            conn.execute(
                """UPDATE documents
                   SET text_preview = ?, chunk_count = ?, status = 'ready'
                   WHERE id = ? AND user_id = ?""",
                (preview, chunk_count, doc_id, user_id),
            )
            conn.commit()
        finally:
            conn.close()

    def count_for_user(self, user_id: int) -> int:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM documents WHERE user_id = ? AND status = 'ready'",
                (user_id,),
            ).fetchone()
            return int(row["n"])
        finally:
            conn.close()

    def delete(self, doc_id: int, user_id: int) -> None:
        """Delete document, its chunks, ChromaDB vectors, and the stored file.

        Vector deletion happens FIRST via VectorService.delete_document.
        If it fails, RuntimeError propagates without touching SQLite rows,
        so nothing is half-deleted. Chunk rows, the document row, and the
        stored file are preserved for the repair script.
        """
        from app.services import vector_service

        conn = self._connect()
        try:
            # Get stored_path before any deletions
            row = conn.execute(
                "SELECT stored_path FROM documents WHERE id = ? AND user_id = ?", (doc_id, user_id)
            ).fetchone()
            stored_path = row["stored_path"] if row else None

            # Delete vectors from ChromaDB FIRST, using VectorService (with retry).
            # If this fails, raise RuntimeError before any SQLite change so nothing
            # is half-deleted. Chunk rows below will be preserved.
            vs = vector_service.get_vector_service()
            vs.delete_document(doc_id, user_id)

            # Delete chunks from SQLite
            from app.database.repositories import ChunkRepository
            chunk_repo = ChunkRepository()
            chunk_repo.delete_for_document(doc_id, user_id)

            # Delete document
            conn.execute("DELETE FROM documents WHERE id = ? AND user_id = ?", (doc_id, user_id))
            conn.commit()

            # Delete stored file
            if stored_path:
                path = Path(stored_path)
                if path.exists():
                    path.unlink(missing_ok=True)
                    # Try to remove empty user directory
                    try:
                        path.parent.rmdir()
                    except OSError:
                        pass  # Directory not empty or doesn't exist
        finally:
            conn.close()


class ChunkRepository(BaseRepository):
    def create(
        self, document_id: int, user_id: int, chunk_index: int,
        content: str, token_count: int, chroma_id: str,
    ) -> DocumentChunk:
        conn = self._connect()
        try:
            cur = conn.execute(
                """INSERT INTO document_chunks
                   (document_id, user_id, chunk_index, content, token_count, chroma_id)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (document_id, user_id, chunk_index, content, token_count, chroma_id),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM document_chunks WHERE id = ?", (cur.lastrowid,)
            ).fetchone()
            return self._row_to_dataclass(row, DocumentChunk)
        finally:
            conn.close()

    def list_for_document(self, doc_id: int, user_id: int) -> List[DocumentChunk]:
        conn = self._connect()
        try:
            rows = conn.execute(
                """SELECT * FROM document_chunks
                   WHERE document_id = ? AND user_id = ? ORDER BY chunk_index""",
                (doc_id, user_id),
            ).fetchall()
            return [self._row_to_dataclass(r, DocumentChunk) for r in rows]
        finally:
            conn.close()

    def delete_for_document(self, doc_id: int, user_id: int) -> List[str]:
        """Delete chunks; return chroma ids so the caller can purge the vector DB."""
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT chroma_id FROM document_chunks WHERE document_id = ? AND user_id = ?",
                (doc_id, user_id),
            ).fetchall()
            ids = [r["chroma_id"] for r in rows]
            conn.execute(
                "DELETE FROM document_chunks WHERE document_id = ? AND user_id = ?",
                (doc_id, user_id),
            )
            conn.commit()
            return ids
        finally:
            conn.close()


class ConversationRepository(BaseRepository):
    def create(self, user_id: int, title: Optional[str] = None) -> Conversation:
        conn = self._connect()
        try:
            cur = conn.execute(
                "INSERT INTO conversations (user_id, title) VALUES (?, ?)", (user_id, title)
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM conversations WHERE id = ?", (cur.lastrowid,)
            ).fetchone()
            return self._row_to_dataclass(row, Conversation)
        finally:
            conn.close()

    def get_by_id(self, convo_id: int, user_id: int) -> Optional[Conversation]:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM conversations WHERE id = ? AND user_id = ?",
                (convo_id, user_id),
            ).fetchone()
            return self._row_to_dataclass(row, Conversation) if row else None
        finally:
            conn.close()

    def list_for_user(self, user_id: int) -> List[Conversation]:
        conn = self._connect()
        try:
            rows = conn.execute(
                """SELECT c.*, (SELECT COUNT(*) FROM messages m
                                 WHERE m.conversation_id = c.id) AS message_count
                   FROM conversations c
                   WHERE c.user_id = ?
                   ORDER BY c.updated_at DESC, c.id DESC""",
                (user_id,),
            ).fetchall()
            out = []
            for r in rows:
                d = dict(r)
                d.pop("message_count", None)
                out.append(Conversation(**d))
            return out
        finally:
            conn.close()

    def update_title(self, convo_id: int, user_id: int, title: str) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "UPDATE conversations SET title = ?, updated_at = datetime('now') "
                "WHERE id = ? AND user_id = ?",
                (title, convo_id, user_id),
            )
            conn.commit()
        finally:
            conn.close()

    def touch(self, convo_id: int, user_id: int) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "UPDATE conversations SET updated_at = datetime('now') "
                "WHERE id = ? AND user_id = ?",
                (convo_id, user_id),
            )
            conn.commit()
        finally:
            conn.close()

    def delete(self, convo_id: int, user_id: int) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "DELETE FROM conversations WHERE id = ? AND user_id = ?", (convo_id, user_id)
            )
            conn.commit()
        finally:
            conn.close()


class MessageRepository(BaseRepository):
    def create(
        self, conversation_id: int, user_id: int, role: str,
        content: str, sources: Optional[list] = None,
        scope: Optional[dict | str] = None,
    ) -> Message:
        conn = self._connect()
        try:
            scope_str = json.dumps(scope) if isinstance(scope, dict) else scope
            cur = conn.execute(
                """INSERT INTO messages
                   (conversation_id, user_id, role, content, sources, scope)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    conversation_id,
                    user_id,
                    role,
                    content,
                    json.dumps(sources) if sources is not None else None,
                    scope_str,
                ),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM messages WHERE id = ?", (cur.lastrowid,)).fetchone()
            return self._row_to_dataclass(row, Message)
        finally:
            conn.close()

    def list_for_conversation(self, conversation_id: int, user_id: int) -> List[Message]:
        conn = self._connect()
        try:
            rows = conn.execute(
                """SELECT * FROM messages
                   WHERE conversation_id = ? AND user_id = ?
                   ORDER BY id""",
                (conversation_id, user_id),
            ).fetchall()
            return [self._row_to_dataclass(r, Message) for r in rows]
        finally:
            conn.close()

    def search(
        self, user_id: int, query: str, limit: int = 50
    ) -> List[Message]:
        conn = self._connect()
        try:
            like = f"%{query}%"
            rows = conn.execute(
                """SELECT m.* FROM messages m
                   JOIN conversations c ON c.id = m.conversation_id
                   WHERE c.user_id = ? AND m.content LIKE ?
                   ORDER BY m.id DESC LIMIT ?""",
                (user_id, like, limit),
            ).fetchall()
            return [self._row_to_dataclass(r, Message) for r in rows]
        finally:
            conn.close()


class SummaryRepository(BaseRepository):
    def create(self, document_id: int, user_id: int, summary_text: str) -> Summary:
        conn = self._connect()
        try:
            cur = conn.execute(
                "INSERT INTO summaries (document_id, user_id, summary_text) VALUES (?, ?, ?)",
                (document_id, user_id, summary_text),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM summaries WHERE id = ?", (cur.lastrowid,)).fetchone()
            return self._row_to_dataclass(row, Summary)
        finally:
            conn.close()

    def list_for_document(self, document_id: int, user_id: int) -> List[Summary]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM summaries WHERE document_id = ? AND user_id = ? ORDER BY id DESC",
                (document_id, user_id),
            ).fetchall()
            return [self._row_to_dataclass(r, Summary) for r in rows]
        finally:
            conn.close()

    def list_for_user(self, user_id: int) -> List[Summary]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM summaries WHERE user_id = ? ORDER BY id DESC", (user_id,)
            ).fetchall()
            return [self._row_to_dataclass(r, Summary) for r in rows]
        finally:
            conn.close()

    def delete_for_document(self, document_id: int, user_id: int) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "DELETE FROM summaries WHERE document_id = ? AND user_id = ?",
                (document_id, user_id),
            )
            conn.commit()
        finally:
            conn.close()


class EventRepository(BaseRepository):
    def create(
        self,
        user_id: int,
        event_text: str,
        document_id: Optional[int] = None,
        event_date: Optional[str] = None,
        raw_date: Optional[str] = None,
    ) -> Event:
        conn = self._connect()
        try:
            cur = conn.execute(
                """INSERT INTO events
                   (user_id, document_id, event_text, event_date, raw_date)
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, document_id, event_text, event_date, raw_date),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM events WHERE id = ?", (cur.lastrowid,)).fetchone()
            return self._row_to_dataclass(row, Event)
        finally:
            conn.close()

    def get_by_id(self, event_id: int, user_id: int) -> Optional[Event]:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM events WHERE id = ? AND user_id = ?", (event_id, user_id)
            ).fetchone()
            return self._row_to_dataclass(row, Event) if row else None
        finally:
            conn.close()

    def list_for_user(self, user_id: int, status: Optional[str] = None) -> List[Event]:
        conn = self._connect()
        try:
            if status:
                rows = conn.execute(
                    "SELECT * FROM events WHERE user_id = ? AND status = ? ORDER BY id",
                    (user_id, status),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM events WHERE user_id = ? ORDER BY id", (user_id,)
                ).fetchall()
            return [self._row_to_dataclass(r, Event) for r in rows]
        finally:
            conn.close()

    def set_status(self, event_id: int, user_id: int, status: str) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "UPDATE events SET status = ? WHERE id = ? AND user_id = ?",
                (status, event_id, user_id),
            )
            conn.commit()
        finally:
            conn.close()

    def delete(self, event_id: int, user_id: int) -> None:
        conn = self._connect()
        try:
            logger.debug("delete: event_id=%s, user_id=%s", event_id, user_id)
            cursor = conn.execute("DELETE FROM events WHERE id = ? AND user_id = ?", (event_id, user_id))
            logger.debug("delete: rowcount=%s", cursor.rowcount)
            conn.commit()
            logger.debug("delete: committed")
        finally:
            conn.close()

    def delete_for_document(self, document_id: int, user_id: int) -> None:
        """Delete all events extracted from a document (reminders cascade)."""
        conn = self._connect()
        try:
            conn.execute(
                "DELETE FROM events WHERE document_id = ? AND user_id = ?",
                (document_id, user_id),
            )
            conn.commit()
        finally:
            conn.close()

    def list_in_date_range(
        self,
        user_id: int,
        start_date: str,
        end_date: str,
        statuses: Optional[List[str]] = None,
    ) -> List[Event]:
        conn = self._connect()
        try:
            query = """
                SELECT * FROM events
                WHERE user_id = ?
                  AND event_date IS NOT NULL
                  AND SUBSTR(event_date, 1, 10) >= ?
                  AND SUBSTR(event_date, 1, 10) <= ?
            """
            params: list = [user_id, start_date, end_date]
            if statuses:
                placeholders = ",".join("?" for _ in statuses)
                query += f" AND status IN ({placeholders})"
                params.extend(statuses)
            query += " ORDER BY event_date ASC, id ASC"
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_dataclass(r, Event) for r in rows]
        finally:
            conn.close()


class ReminderRepository(BaseRepository):
    def create(
        self,
        user_id: int,
        event_id: int,
        remind_at: str,
        subject: Optional[str] = None,
        body: Optional[str] = None,
        channel: str = "email",
        status: str = "scheduled",
        google_event_id: Optional[str] = None,
        sync_status: str = "not_synced",
        sync_error: Optional[str] = None,
    ) -> Reminder:
        conn = self._connect()
        try:
            cur = conn.execute(
                """INSERT INTO reminders
                   (user_id, event_id, remind_at, channel, subject, body, status,
                    google_event_id, sync_status, sync_error)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    user_id,
                    event_id,
                    remind_at,
                    channel,
                    subject,
                    body,
                    status,
                    google_event_id,
                    sync_status,
                    sync_error,
                ),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM reminders WHERE id = ?", (cur.lastrowid,)).fetchone()
            return self._row_to_dataclass(row, Reminder)
        finally:
            conn.close()

    def update_google_sync(
        self,
        reminder_id: int,
        user_id: int,
        sync_status: str,
        google_event_id: Optional[str] = None,
        sync_error: Optional[str] = None,
    ) -> None:
        conn = self._connect()
        try:
            conn.execute(
                """UPDATE reminders
                   SET sync_status = ?, google_event_id = ?, sync_error = ?
                   WHERE id = ? AND user_id = ?""",
                (sync_status, google_event_id, sync_error, reminder_id, user_id),
            )
            conn.commit()
        finally:
            conn.close()

    def get_by_id(self, reminder_id: int, user_id: int) -> Optional[Reminder]:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM reminders WHERE id = ? AND user_id = ?",
                (reminder_id, user_id),
            ).fetchone()
            return self._row_to_dataclass(row, Reminder) if row else None
        finally:
            conn.close()

    def list_for_user(self, user_id: int, status: Optional[str] = None) -> List[Reminder]:
        conn = self._connect()
        try:
            if status:
                rows = conn.execute(
                    """SELECT r.* FROM reminders r
                       JOIN events e ON e.id = r.event_id
                       WHERE r.user_id = ? AND r.status = ?
                       ORDER BY r.remind_at""",
                    (user_id, status),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT r.* FROM reminders r
                       JOIN events e ON e.id = r.event_id
                       WHERE r.user_id = ?
                       ORDER BY r.remind_at""",
                    (user_id,),
                ).fetchall()
            return [self._row_to_dataclass(r, Reminder) for r in rows]
        finally:
            conn.close()

    def due_scheduled(self, user_id: int, now_iso: str) -> List[Reminder]:
        """Scheduled reminders whose remind_at is at or before now and whose event is confirmed."""
        conn = self._connect()
        try:
            rows = conn.execute(
                """SELECT r.* FROM reminders r
                   JOIN events e ON e.id = r.event_id
                   WHERE r.user_id = ? AND r.status = 'scheduled'
                     AND e.status = 'confirmed' AND r.remind_at <= ?
                   ORDER BY r.remind_at""",
                (user_id, now_iso),
            ).fetchall()
            return [self._row_to_dataclass(r, Reminder) for r in rows]
        finally:
            conn.close()

    def set_status(
        self, reminder_id: int, user_id: int, status: str, sent_at: Optional[str] = None
    ) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "UPDATE reminders SET status = ?, sent_at = ? WHERE id = ? AND user_id = ?",
                (status, sent_at, reminder_id, user_id),
            )
            conn.commit()
        finally:
            conn.close()

    def delete(self, reminder_id: int, user_id: int) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "DELETE FROM reminders WHERE id = ? AND user_id = ?", (reminder_id, user_id)
            )
            conn.commit()
        finally:
            conn.close()

    def list_in_date_range(
        self,
        user_id: int,
        start_date: str,
        end_date: str,
        statuses: Optional[List[str]] = None,
    ) -> List[Reminder]:
        conn = self._connect()
        try:
            query = """
                SELECT * FROM reminders
                WHERE user_id = ?
                  AND remind_at IS NOT NULL
                  AND SUBSTR(remind_at, 1, 10) >= ?
                  AND SUBSTR(remind_at, 1, 10) <= ?
            """
            params: list = [user_id, start_date, end_date]
            if statuses:
                placeholders = ",".join("?" for _ in statuses)
                query += f" AND status IN ({placeholders})"
                params.extend(statuses)
            query += " ORDER BY remind_at ASC, id ASC"
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_dataclass(r, Reminder) for r in rows]
        finally:
            conn.close()


class NotificationLogRepository(BaseRepository):
    def log(
        self,
        kind: str,
        success: bool,
        detail: Optional[str] = None,
        user_id: Optional[int] = None,
        reminder_id: Optional[int] = None,
    ) -> NotificationLog:
        conn = self._connect()
        try:
            cur = conn.execute(
                """INSERT INTO notification_logs
                   (user_id, reminder_id, kind, success, detail)
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, reminder_id, kind, int(bool(success)), detail),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM notification_logs WHERE id = ?", (cur.lastrowid,)
            ).fetchone()
            return self._row_to_dataclass(row, NotificationLog)
        finally:
            conn.close()

    def recent(self, limit: int = 20) -> List[NotificationLog]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM notification_logs ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [self._row_to_dataclass(r, NotificationLog) for r in rows]
        finally:
            conn.close()


class GoogleConnectionRepository(BaseRepository):
    def get_by_user_id(self, user_id: int) -> Optional[GoogleConnection]:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM google_connections WHERE user_id = ?", (user_id,)
            ).fetchone()
            if not row:
                return None
            return self._row_to_dataclass(row, GoogleConnection)
        finally:
            conn.close()

    def upsert(
        self,
        user_id: int,
        google_email: str,
        refresh_token_encrypted: str,
        scope: str,
    ) -> GoogleConnection:
        conn = self._connect()
        try:
            conn.execute(
                """INSERT INTO google_connections
                   (user_id, google_email, refresh_token_encrypted, scope)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET
                       google_email = excluded.google_email,
                       refresh_token_encrypted = excluded.refresh_token_encrypted,
                       scope = excluded.scope,
                       connected_at = CURRENT_TIMESTAMP""",
                (user_id, google_email, refresh_token_encrypted, scope),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM google_connections WHERE user_id = ?", (user_id,)
            ).fetchone()
            return self._row_to_dataclass(row, GoogleConnection)
        finally:
            conn.close()

    def delete_by_user_id(self, user_id: int) -> bool:
        conn = self._connect()
        try:
            cur = conn.execute(
                "DELETE FROM google_connections WHERE user_id = ?", (user_id,)
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()


class DocumentLinkRepository(BaseRepository):
    def replace_links_for_user(self, user_id: int, links: List[dict]) -> None:
        """Replace all document links for a user in a single transaction.

        Args:
            user_id: The user ID.
            links: List of dicts with keys: doc_a, doc_b, score, shared_terms.
                   doc_a must be < doc_b.
        """
        conn = self._connect()
        try:
            conn.execute("DELETE FROM document_links WHERE user_id = ?", (user_id,))
            if links:
                conn.executemany(
                    """INSERT INTO document_links
                       (user_id, doc_a, doc_b, score, shared_terms)
                       VALUES (?, ?, ?, ?, ?)""",
                    [(user_id, link["doc_a"], link["doc_b"], link["score"], link["shared_terms"])
                     for link in links],
                )
            conn.commit()
        finally:
            conn.close()

    def list_links(self, user_id: int) -> List[DocumentLink]:
        """List all document links for a user."""
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM document_links WHERE user_id = ? ORDER BY score DESC",
                (user_id,),
            ).fetchall()
            return [self._row_to_dataclass(r, DocumentLink) for r in rows]
        finally:
            conn.close()

    def list_links_for_document(self, user_id: int, doc_id: int) -> List[DocumentLink]:
        """List document links involving a specific document."""
        conn = self._connect()
        try:
            rows = conn.execute(
                """SELECT * FROM document_links
                   WHERE user_id = ? AND (doc_a = ? OR doc_b = ?)
                   ORDER BY score DESC""",
                (user_id, doc_id, doc_id),
            ).fetchall()
            return [self._row_to_dataclass(r, DocumentLink) for r in rows]
        finally:
            conn.close()
