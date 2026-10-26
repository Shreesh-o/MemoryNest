"""Dashboard router: stats, upcoming deadlines, recent activity."""

from __future__ import annotations


from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.api.schemas import (
    ConversationPublic,
    DocumentPublic,
    EventPublic,
)
from app.database.models import User
from app.services.dashboard_service import DashboardData, get_dashboard

router = APIRouter()


def _doc_to_public(doc) -> DocumentPublic:
    return DocumentPublic(
        id=doc.id,
        filename=doc.filename,
        file_type=doc.file_type,
        status=doc.status,
        chunk_count=doc.chunk_count,
        error_message=doc.error_message,
        created_at=doc.created_at,
        text_preview=doc.text_preview,
    )


def _event_to_public(ev) -> EventPublic:
    return EventPublic(
        id=ev.id,
        user_id=ev.user_id,
        event_text=ev.event_text,
        document_id=ev.document_id,
        event_date=ev.event_date,
        raw_date=ev.raw_date,
        status=ev.status,
        created_at=ev.created_at,
    )


def _convo_to_public(c) -> ConversationPublic:
    return ConversationPublic(
        id=c.id,
        user_id=c.user_id,
        title=c.title,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


@router.get("/api/dashboard")
def api_dashboard(user: User = Depends(get_current_user)):
    """Get dashboard data for the current user."""
    data: DashboardData = get_dashboard(user.id)
    return {
        "total_documents": data.total_documents,
        "ready_documents": data.ready_documents,
        "failed_documents": data.failed_documents,
        "pending_documents": data.pending_documents,
        "total_chunks": data.total_chunks,
        "pending_events": [_event_to_public(e) for e in data.pending_events],
        "confirmed_events": [_event_to_public(e) for e in data.confirmed_events],
        "upcoming_deadlines": [_event_to_public(e) for e in data.upcoming_deadlines],
        "recent_conversations": [_convo_to_public(c) for c in data.recent_conversations],
    }