"""Reminders router: events, reminders, and calendar export."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.api.deps import get_current_user
from app.api.schemas import (
    CheckRemindersResponse,
    ConfirmEventRequest,
    EventExtractResponse,
    EventPublic,
    ReminderPublic,
)
from app.database.models import User
from app.services.reminder_flow_service import (
    build_ics_for_user,
    check_and_send_due,
    confirm_event,
    discard_event,
    extract_events_for_document,
    list_events,
    list_reminders,
)

router = APIRouter()


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


def _reminder_to_public(r) -> ReminderPublic:
    return ReminderPublic(
        id=r.id,
        user_id=r.user_id,
        event_id=r.event_id,
        remind_at=r.remind_at,
        channel=r.channel,
        subject=r.subject,
        body=r.body,
        status=r.status,
        sent_at=r.sent_at,
        created_at=r.created_at,
    )


@router.get("/api/events", response_model=List[EventPublic])
def api_list_events(
    status: Optional[str] = Query(None, description="Filter by status: pending, confirmed, skipped"),
    user: User = Depends(get_current_user),
):
    """List events for the current user, optionally filtered by status."""
    events = list_events(user.id, status)
    return [_event_to_public(e) for e in events]


@router.post("/api/documents/{doc_id}/extract-events", response_model=EventExtractResponse, status_code=status.HTTP_201_CREATED)
def api_extract_events(
    doc_id: int,
    user: User = Depends(get_current_user),
):
    """Extract events from a document and create Event records."""
    try:
        events = extract_events_for_document(user.id, doc_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    return EventExtractResponse(events=[_event_to_public(e) for e in events])


@router.post("/api/events/{event_id}/confirm", response_model=EventPublic)
def api_confirm_event(
    event_id: int,
    req: ConfirmEventRequest,
    user: User = Depends(get_current_user),
):
    """Confirm an event and create a reminder."""
    try:
        ev, _ = confirm_event(user.id, event_id, req.remind_at)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return _event_to_public(ev)


@router.post("/api/events/{event_id}/discard", status_code=status.HTTP_204_NO_CONTENT)
def api_discard_event(
    event_id: int,
    user: User = Depends(get_current_user),
):
    """Discard (delete) an event."""
    try:
        discard_event(user.id, event_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/api/reminders", response_model=List[ReminderPublic])
def api_list_reminders(
    user: User = Depends(get_current_user),
):
    """List all reminders for the current user."""
    reminders = list_reminders(user.id)
    return [_reminder_to_public(r) for r in reminders]


@router.get("/api/calendar.ics")
def api_calendar_ics(
    event_ids: Optional[str] = Query(None, description="Comma-separated event IDs to include"),
    user: User = Depends(get_current_user),
):
    """Export calendar as .ics file."""
    ids = None
    if event_ids:
        try:
            ids = [int(x.strip()) for x in event_ids.split(",") if x.strip()]
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid event_ids format")

    ics_bytes = build_ics_for_user(user.id, ids)
    return Response(
        content=ics_bytes,
        media_type="text/calendar",
        headers={"Content-Disposition": 'attachment; filename="memorynest.ics"'},
    )


@router.post("/api/reminders/check", response_model=CheckRemindersResponse)
def api_check_reminders(
    user: User = Depends(get_current_user),
):
    """Check for due reminders and send them."""
    result = check_and_send_due(user.id)
    return CheckRemindersResponse(
        sent=result.sent,
        failed=result.failed,
        details=[{"reminder_id": d[0], "success": d[1], "detail": d[2]} for d in result.details],
    )