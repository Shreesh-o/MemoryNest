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


class UpdateEmailRequest(BaseModel):
    email: Optional[str] = None


class UpdateProfileRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class DeactivateAccountRequest(BaseModel):
    password: Optional[str] = None


class DocumentPublic(BaseModel):
    id: int
    filename: str
    file_type: str
    size_bytes: int = 0
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
    email_status: Optional[str] = None
    google_status: Optional[str] = None


class ConfirmEventResponse(EventPublic):
    email_status: str
    google_status: Optional[str] = None


class EventExtractResponse(BaseModel):
    events: List[EventPublic]


class ConfirmEventRequest(BaseModel):
    remind_at: Optional[str] = None
    lead_minutes: Optional[int] = None


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
    google_event_id: Optional[str] = None
    sync_status: str = "not_synced"
    sync_error: Optional[str] = None
    created_at: Optional[str] = None


class CalendarItem(BaseModel):
    id: int
    kind: str
    title: str
    date: str
    all_day: bool
    status: str
    document_id: Optional[int] = None
    event_id: Optional[int] = None
    sync_status: Optional[str] = None


class CheckRemindersResponse(BaseModel):
    configured: bool
    sent: int
    failed: int
    skipped: int
    errors: List[str]
    details: List[dict] = []


class ChatMessage(BaseModel):
    role: str
    content: str
    sources: Optional[List[dict]] = None
    scope: Optional[dict] = None
    created_at: Optional[str] = None


class ChatRequest(BaseModel):
    question: str = Field(..., max_length=2000)
    conversation_id: Optional[int] = None
    document_ids: Optional[List[int]] = None


class ChatResponse(BaseModel):
    conversation_id: int
    answer: str
    sources: List[dict] = []
    scope: Optional[dict] = None


class ChatDocumentItem(BaseModel):
    id: int
    filename: str
    file_type: str


class ConversationPublic(BaseModel):
    id: int
    user_id: int
    title: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    messages: Optional[List[ChatMessage]] = None


class SummaryPublic(BaseModel):
    id: int
    document_id: int
    user_id: int
    summary_text: str
    created_at: Optional[str] = None


class SummaryCreateRequest(BaseModel):
    force: bool = False


class SummaryAudioResponse(BaseModel):
    engine: str
    url: str


class SearchHit(BaseModel):
    document_id: int
    filename: str
    chunk_index: int
    snippet: str
    similarity: float


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    top_k: Optional[int] = Field(default=8, ge=1, le=20)
    document_ids: Optional[List[int]] = Field(default=None, description="Optional document IDs to scope search to")


class SearchResponse(BaseModel):
    query: str
    hits: List[SearchHit]


class GoogleStatusResponse(BaseModel):
    configured: bool
    connected: bool
    google_email: Optional[str] = None


class GoogleConnectResponse(BaseModel):
    auth_url: str


class GoogleDisconnectResponse(BaseModel):
    status: str = "ok"
    disconnected: bool = True


class GraphNode(BaseModel):
    id: int
    label: str
    file_type: str
    link_count: int


class GraphEdge(BaseModel):
    source: int
    target: int
    score: float
    shared_terms: List[str]


class GraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    unlinked: List[GraphNode]


class RelatedDocument(BaseModel):
    id: int
    filename: str
    file_type: str
    score: float
    shared_terms: List[str]


class RelatedResponse(BaseModel):
    related: List[RelatedDocument]


class GraphRefreshResponse(BaseModel):
    documents: int
    edges: int
