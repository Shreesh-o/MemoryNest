"""Dataclasses mirroring the SQLite schema (one per table)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class User:
    id: int
    username: str
    password_hash: str
    email: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class Document:
    id: int
    user_id: int
    filename: str
    stored_path: str
    file_type: str
    size_bytes: int = 0
    status: str = "uploaded"
    error_message: Optional[str] = None
    text_preview: Optional[str] = None
    chunk_count: int = 0
    created_at: Optional[str] = None


@dataclass
class DocumentChunk:
    id: int
    document_id: int
    user_id: int
    chunk_index: int
    content: str
    token_count: int = 0
    chroma_id: str = ""


@dataclass
class Conversation:
    id: int
    user_id: int
    title: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class Message:
    id: int
    conversation_id: int
    user_id: int
    role: str
    content: str
    sources: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class Summary:
    id: int
    document_id: int
    user_id: int
    summary_text: str
    created_at: Optional[str] = None


@dataclass
class Event:
    id: int
    user_id: int
    event_text: str
    document_id: Optional[int] = None
    event_date: Optional[str] = None
    raw_date: Optional[str] = None
    status: str = "pending"
    created_at: Optional[str] = None


@dataclass
class Reminder:
    id: int
    user_id: int
    event_id: int
    remind_at: str
    channel: str = "email"
    subject: Optional[str] = None
    body: Optional[str] = None
    status: str = "scheduled"
    sent_at: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class NotificationLog:
    id: int
    user_id: Optional[int]
    reminder_id: Optional[int]
    kind: str
    success: bool
    detail: Optional[str] = None
    created_at: Optional[str] = None
