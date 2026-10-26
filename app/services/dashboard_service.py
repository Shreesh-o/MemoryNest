"""Dashboard service: business logic for dashboard stats and summary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from app.database.models import Conversation, Event
from app.database.repositories import (
    ConversationRepository,
    DocumentRepository,
    EventRepository,
)


@dataclass
class DashboardData:
    """Dashboard data for a user."""

    total_documents: int
    ready_documents: int
    failed_documents: int
    pending_documents: int
    total_chunks: int
    pending_events: List[Event]
    confirmed_events: List[Event]
    upcoming_deadlines: List[Event]
    recent_conversations: List[Conversation]


def get_dashboard(user_id: int) -> DashboardData:
    """Get dashboard data for a user.

    Args:
        user_id: The user ID.

    Returns:
        DashboardData with all dashboard stats and recent items.
    """
    doc_repo = DocumentRepository()
    convo_repo = ConversationRepository()
    ev_repo = EventRepository()

    # Documents stats
    docs = doc_repo.list_for_user(user_id)
    ready_docs = [d for d in docs if d.status == "ready"]
    failed_docs = [d for d in docs if d.status == "error"]
    pending_docs = [d for d in docs if d.status not in ("ready", "error")]
    total_chunks = sum(d.chunk_count for d in ready_docs)

    # Events
    pending_events = ev_repo.list_for_user(user_id, status="pending")
    confirmed_events = ev_repo.list_for_user(user_id, status="confirmed")

    # Upcoming deadlines: confirmed events with dates, sorted by date
    upcoming = [
        e
        for e in confirmed_events
        if e.event_date
    ]
    upcoming.sort(key=lambda e: e.event_date or "")
    upcoming_deadlines = upcoming[:5]

    # Recent conversations
    recent_conversations = convo_repo.list_for_user(user_id)[:5]

    return DashboardData(
        total_documents=len(docs),
        ready_documents=len(ready_docs),
        failed_documents=len(failed_docs),
        pending_documents=len(pending_docs),
        total_chunks=total_chunks,
        pending_events=pending_events,
        confirmed_events=confirmed_events,
        upcoming_deadlines=upcoming_deadlines,
        recent_conversations=recent_conversations,
    )