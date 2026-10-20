"""Pydantic schemas for the FastAPI layer."""

from __future__ import annotations

from typing import Optional, List

from pydantic import BaseModel, Field


class UserPublic(BaseModel):
    id: int
    username: str
    email: Optional[str] = None


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class DocumentPublic(BaseModel):
    id: int
    filename: str
    file_type: str
    status: str
    chunk_count: int
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    text_preview: Optional[str] = None


class IngestResultResponse(BaseModel):
    filename: str
    status: str
    message: str
    doc_id: Optional[int] = None
    chunk_count: int


class EventPublic(BaseModel):
    id: int
    user_id: int
    event_text: str
    document_id: Optional[int] = None
    event_date: Optional[str] = None
    raw_date: Optional[str] = None
    status: str
    created_at: Optional[str] = None


class EventExtractResponse(BaseModel):
    events: List[EventPublic]


class ConfirmEventRequest(BaseModel):
    remind_at: Optional[str] = None


class ReminderPublic(BaseModel):
    id: int
    user_id: int
    event_id: int
    remind_at: str
    channel: str
    subject: Optional[str] = None
    body: Optional[str] = None
    status: str
    sent_at: Optional[str] = None
    created_at: Optional[str] = None


class CheckRemindersResponse(BaseModel):
    sent: int
    failed: int
    details: List[dict]