"""Reminder flow service: business logic for events and reminders.

No Streamlit imports. Pure business logic for API and page use.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple

from app.database.repositories import DocumentRepository, EventRepository, ReminderRepository
from app.services import event_service, email_service, ics_service
from app.database.models import Event, Reminder
from app.utils.config import EMAIL_USERNAME, EMAIL_APP_PASSWORD, RECIPIENT_EMAIL

logger = logging.getLogger(__name__)


@dataclass
class CheckResult:
    sent: int
    failed: int
    details: List[Tuple[int, bool, str]]  # (reminder_id, success, detail)


def extract_events_for_document(user_id: int, doc_id: int) -> List[Event]:
    """Extract events from a document and create Event records.

    Args:
        user_id: The user who owns the document.
        doc_id: The document ID to extract events from.

    Returns:
        List of created Event objects.

    Raises:
        ValueError: If document not found, not ready, or no text preview.
        RuntimeError: If event extraction fails.
    """
    doc_repo = DocumentRepository()
    ev_repo = EventRepository()

    doc = doc_repo.get_by_id(doc_id, user_id)
    if not doc:
        raise ValueError("Document not found")
    if doc.status != "ready":
        raise ValueError("Document is not ready for extraction")
    text = doc.text_preview or ""
    if not text:
        raise ValueError("Document has no text preview")

    # Check if events already exist for this document
    existing_events = ev_repo.list_for_user(user_id)
    existing_for_doc = [e for e in existing_events if e.document_id == doc_id]
    if existing_for_doc:
        # Return existing events instead of creating duplicates
        return existing_for_doc

    try:
        extracted = event_service.extract_events(text)
    except Exception as e:
        logger.exception("Event extraction failed for doc %s", doc_id)
        raise RuntimeError(f"Event extraction failed: {e}")

    if not extracted:
        return []

    created = []
    for e in extracted:
        ev = ev_repo.create(
            user_id=user_id,
            event_text=e["event_text"],
            document_id=doc.id,
            event_date=e.get("event_date"),
            raw_date=e.get("raw_date"),
        )
        created.append(ev)

    return created


def list_events(user_id: int, status: Optional[str] = None) -> List[Event]:
    """List events for a user, optionally filtered by status."""
    ev_repo = EventRepository()
    return ev_repo.list_for_user(user_id, status)


def confirm_event(
    user_id: int,
    event_id: int,
    remind_at: Optional[str] = None,
) -> Tuple[Event, Reminder]:
    """Confirm an event and create a reminder.

    Args:
        user_id: The user who owns the event.
        event_id: The event ID to confirm.
        remind_at: Optional reminder time in ISO format (e.g., "2026-10-15 09:00:00").
                   If not provided, defaults to event_date at 09:00 or today at 09:00.

    Returns:
        Tuple of (confirmed Event, created Reminder).

    Raises:
        ValueError: If event not found or already confirmed/skipped.
    """
    ev_repo = EventRepository()
    rem_repo = ReminderRepository()

    ev = ev_repo.get_by_id(event_id, user_id)
    if not ev:
        raise ValueError("Event not found")
    if ev.status != "pending":
        raise ValueError(f"Event is not pending (status: {ev.status})")

    # Confirm the event
    ev_repo.set_status(event_id, user_id, "confirmed")

    # Determine remind_at
    if remind_at is None:
        if ev.event_date:
            remind_at = f"{ev.event_date} 09:00:00"
        else:
            remind_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Create reminder
    reminder = rem_repo.create(
        user_id=user_id,
        event_id=event_id,
        remind_at=remind_at,
        subject=f"Reminder: {ev.event_text[:60]}",
        body=f"Event: {ev.event_text}\nDate: {ev.event_date or 'TBD'}\nRaw: {ev.raw_date or 'N/A'}",
    )

    # Return updated event and reminder
    updated_ev = ev_repo.get_by_id(event_id, user_id)
    return updated_ev, reminder


def discard_event(user_id: int, event_id: int) -> None:
    """Discard (delete) an event. Reminders cascade via FK."""
    ev_repo = EventRepository()

    ev = ev_repo.get_by_id(event_id, user_id)
    if not ev:
        raise ValueError("Event not found")

    ev_repo.delete(event_id, user_id)


def list_reminders(user_id: int) -> List[Reminder]:
    """List all reminders for a user (all statuses)."""
    rem_repo = ReminderRepository()
    return rem_repo.list_for_user(user_id)


def build_ics_for_user(user_id: int, event_ids: Optional[List[int]] = None) -> bytes:
    """Build an ICS calendar for the user's events.

    Args:
        user_id: The user ID.
        event_ids: Optional list of event IDs to include. If None, includes all confirmed events with reminders.

    Returns:
        ICS calendar as bytes.
    """
    ev_repo = EventRepository()
    rem_repo = ReminderRepository()
    doc_repo = DocumentRepository()

    if event_ids is not None:
        events = []
        for eid in event_ids:
            ev = ev_repo.get_by_id(eid, user_id)
            if ev:
                events.append(ev)
        reminders = rem_repo.list_for_user(user_id)
        reminders = [r for r in reminders if r.event_id in {e.id for e in events}]
    else:
        # Default: confirmed events with scheduled reminders
        events = ev_repo.list_for_user(user_id, status="confirmed")
        reminders = rem_repo.list_for_user(user_id, status="scheduled")
        # Filter reminders to only those for confirmed events
        confirmed_event_ids = {e.id for e in events}
        reminders = [r for r in reminders if r.event_id in confirmed_event_ids]

    # Get user email
    from app.database.repositories import UserRepository
    user_repo = UserRepository()
    user = user_repo.get_by_id(user_id)
    user_email = user.email if user else None

    return ics_service.build_ics_from_events_and_reminders(events, reminders, user_email)


def check_and_send_due(user_id: int) -> CheckResult:
    """Check for due reminders and send them.

    Args:
        user_id: The user ID.

    Returns:
        CheckResult with counts and details.
    """
    from app.utils.config import EMAIL_USERNAME, EMAIL_APP_PASSWORD, RECIPIENT_EMAIL

    rem_repo = ReminderRepository()
    now = datetime.now().isoformat()
    due = rem_repo.due_scheduled(user_id, now)

    if not due:
        return CheckResult(sent=0, failed=0, details=[])

    # Check email config
    if not EMAIL_USERNAME or not EMAIL_APP_PASSWORD or not RECIPIENT_EMAIL:
        details = [(r.id, False, "Email not configured") for r in due]
        return CheckResult(sent=0, failed=len(due), details=details)

    sent = 0
    failed = 0
    details = []

    for r in due:
        try:
            ok, detail = email_service.send_reminder_email(r.subject or "", r.body or "")
            if ok:
                rem_repo.set_status(r.id, user_id, "sent", datetime.now().isoformat())
                sent += 1
                details.append((r.id, True, "sent"))
            else:
                rem_repo.set_status(r.id, user_id, "failed")
                failed += 1
                details.append((r.id, False, detail))
        except Exception as e:
            rem_repo.set_status(r.id, user_id, "failed")
            failed += 1
            logger.exception("Failed to send reminder %s", r.id)
            details.append((r.id, False, f"Exception: {e}"))

    return CheckResult(sent=sent, failed=failed, details=details)