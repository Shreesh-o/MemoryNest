"""Thin data-access layer over SQLite. One repository per table."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from app.database.database import get_connection
from app.database.models import (
    Conversation,
    Document,
    DocumentChunk,
    Event,
    Message,
    NotificationLog,
    Reminder,
    Summary,
    User,
)


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
            print(f"DEBUG set_text: doc_id={doc_id}, user_id={user_id}, preview={repr(preview)}, chunk_count={chunk_count}")
            conn.execute(
                """UPDATE documents
                   SET text_preview = ?, chunk_count = ?, status = 'ready'
                   WHERE id = ? AND user_id = ?""",
                (preview, chunk_count, doc_id, user_id),
            )
            print(f"DEBUG set_text: rows affected = {conn.total_changes}")
            conn.commit()
            print("DEBUG set_text: commit done")
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
        """Delete document, its chunks, ChromaDB vectors, and the stored file."""
        import os
        from app.services import vector_service
        from app.utils.config import UPLOAD_DIR

        conn = self._connect()
        try:
            # Get stored_path before deleting
            row = conn.execute(
                "SELECT stored_path FROM documents WHERE id = ? AND user_id = ?", (doc_id, user_id)
            ).fetchone()
            stored_path = row["stored_path"] if row else None

            # Delete chunks and get chroma_ids
            from app.database.repositories import ChunkRepository
            chunk_repo = ChunkRepository()
            chroma_ids = chunk_repo.delete_for_document(doc_id, user_id)

            # Delete vectors from ChromaDB
            if chroma_ids:
                vs = vector_service.get_vector_service()
                vs.collection.delete(ids=chroma_ids)

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
    ) -> Message:
        conn = self._connect()
        try:
            cur = conn.execute(
                """INSERT INTO messages
                   (conversation_id, user_id, role, content, sources)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    conversation_id,
                    user_id,
                    role,
                    content,
                    json.dumps(sources) if sources is not None else None,
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
            conn.execute("DELETE FROM events WHERE id = ? AND user_id = ?", (event_id, user_id))
            conn.commit()
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
    ) -> Reminder:
        conn = self._connect()
        try:
            cur = conn.execute(
                """INSERT INTO reminders
                   (user_id, event_id, remind_at, subject, body)
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, event_id, remind_at, subject, body),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM reminders WHERE id = ?", (cur.lastrowid,)).fetchone()
            return self._row_to_dataclass(row, Reminder)
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
