"""Reminder flow service: business logic for events and reminders.

No Streamlit imports. Pure business logic for API and page use.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple

from app.database.repositories import (
    DocumentRepository,
    EventRepository,
    GoogleConnectionRepository,
    NotificationLogRepository,
    ReminderRepository,
    UserRepository,
)
from app.services import event_service, email_service, ics_service, google_calendar_service
from app.services.google_auth_service import is_google_configured
from app.database.models import Event, Reminder
from app.utils.config import EMAIL_USERNAME, EMAIL_APP_PASSWORD, RECIPIENT_EMAIL

logger = logging.getLogger(__name__)


@dataclass
class CheckResult:
    configured: bool
    sent: int
    failed: int
    skipped: int
    errors: List[str]
    details: List[Tuple[int, bool, str]] = field(default_factory=list)  # (reminder_id, success, detail)


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
) -> Tuple[Event, Reminder, str, str]:
    """Confirm an event and create a reminder.

    Sends a confirmation email to the user's email address if configured.
    Syncs with Google Calendar if the user is connected.
    Returns (confirmed Event, created Reminder, email_status, google_status).

    Args:
        user_id: The user who owns the event.
        event_id: The event ID to confirm.
        remind_at: Optional reminder time in ISO format (e.g., "2026-10-15 09:00:00").
                   If not provided, defaults to event_date at 09:00 or today at 09:00.

    Returns:
        Tuple of (confirmed Event, created Reminder, email_status, google_status).

    Raises:
        ValueError: If event not found or already confirmed/skipped.
    """
    ev_repo = EventRepository()
    rem_repo = ReminderRepository()
    doc_repo = DocumentRepository()
    user_repo = UserRepository()
    log_repo = NotificationLogRepository()

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
            date_part = ev.event_date[:10]
            remind_at = f"{date_part} 09:00:00"
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

    # Check user email and SMTP configuration
    user = user_repo.get_by_id(user_id)
    user_email = (user.email or "").strip() if user else ""

    if not user_email:
        # If user has no email: skip sending
        email_status = "no_email"
    elif not email_service.is_smtp_configured():
        # SMTP not configured: log failure to notification_logs, do not raise
        email_status = "not_configured"
        log_repo.log(
            kind="confirmation",
            success=False,
            detail="SMTP not configured",
            user_id=user_id,
            reminder_id=reminder.id,
        )
    else:
        # Attempt to send confirmation email
        doc_name = None
        if ev.document_id:
            doc = doc_repo.get_by_id(ev.document_id, user_id)
            if doc:
                doc_name = doc.filename

        subject = f"Reminder Confirmation: {ev.event_text[:60]}"
        lines = [
            "Your reminder has been confirmed and scheduled.",
            "",
            f"Event: {ev.event_text}",
            f"Event Date: {ev.event_date or 'TBD'}",
            f"Remind At: {remind_at}",
        ]
        if doc_name:
            lines.append(f"Document: {doc_name}")
        body = "\n".join(lines)

        try:
            ok, detail = email_service.send_reminder_email(
                subject, body, to_address=user_email
            )
            if ok:
                email_status = "sent"
                log_repo.log(
                    kind="confirmation",
                    success=True,
                    detail="sent",
                    user_id=user_id,
                    reminder_id=reminder.id,
                )
            else:
                email_status = "failed"
                log_repo.log(
                    kind="confirmation",
                    success=False,
                    detail=detail,
                    user_id=user_id,
                    reminder_id=reminder.id,
                )
        except Exception as e:
            logger.exception("Failed to send confirmation email for event %s", event_id)
            email_status = "failed"
            log_repo.log(
                kind="confirmation",
                success=False,
                detail=f"Exception: {e}",
                user_id=user_id,
                reminder_id=reminder.id,
            )

    # Google Calendar sync: only attempt if Google is configured and user is connected
    google_status = "not_connected"
    google_conn = GoogleConnectionRepository().get_by_user_id(user_id)
    if is_google_configured() and google_conn:
        try:
            google_event_id = google_calendar_service.create_event(user_id, ev, reminder)
            rem_repo.update_google_sync(
                reminder.id,
                user_id,
                sync_status="synced",
                google_event_id=google_event_id,
                sync_error=None,
            )
            google_status = "synced"
        except Exception as e:
            logger.exception("Google Calendar sync failed on confirm for reminder %s: %s", reminder.id, e)
            still_conn = GoogleConnectionRepository().get_by_user_id(user_id)
            if not still_conn:
                rem_repo.update_google_sync(
                    reminder.id,
                    user_id,
                    sync_status="not_connected",
                    google_event_id=None,
                    sync_error=str(e)[:200],
                )
                google_status = "not_connected"
            else:
                rem_repo.update_google_sync(
                    reminder.id,
                    user_id,
                    sync_status="failed",
                    google_event_id=reminder.google_event_id,
                    sync_error=str(e)[:200],
                )
                google_status = "failed"
    else:
        rem_repo.update_google_sync(
            reminder.id,
            user_id,
            sync_status="not_connected",
            google_event_id=None,
            sync_error=None,
        )
        google_status = "not_connected"

    # Reload reminder with sync fields
    updated_reminder = rem_repo.get_by_id(reminder.id, user_id) or reminder
    updated_ev = ev_repo.get_by_id(event_id, user_id)
    return updated_ev, updated_reminder, email_status, google_status


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


def cancel_reminder(user_id: int, reminder_id: int) -> None:
    """Cancel a reminder: delete Google event if synced, delete the reminder row, and revert event to pending.

    Args:
        user_id: The user ID.
        reminder_id: The reminder ID to cancel.

    Raises:
        ValueError: If reminder not found or not owned by user.
    """
    rem_repo = ReminderRepository()
    ev_repo = EventRepository()

    rem = rem_repo.get_by_id(reminder_id, user_id)
    if not rem:
        raise ValueError("Reminder not found")

    # If linked to a Google Calendar event, attempt deletion (Google errors never block cancel)
    if rem.google_event_id:
        try:
            google_calendar_service.delete_event(user_id, rem.google_event_id)
        except Exception as e:
            logger.warning(
                "Failed to delete Google event %s for reminder %s on cancel: %s",
                rem.google_event_id,
                reminder_id,
                e,
            )

    rem_repo.delete(reminder_id, user_id)
    ev_repo.set_status(rem.event_id, user_id, "pending")


def sync_reminder(user_id: int, reminder_id: int) -> Reminder:
    """Retry Google Calendar sync for a reminder.

    Args:
        user_id: The user ID.
        reminder_id: The reminder ID to retry sync.

    Returns:
        Updated Reminder object.

    Raises:
        ValueError: If reminder or associated event not found.
    """
    rem_repo = ReminderRepository()
    ev_repo = EventRepository()

    rem = rem_repo.get_by_id(reminder_id, user_id)
    if not rem:
        raise ValueError("Reminder not found")

    ev = ev_repo.get_by_id(rem.event_id, user_id)
    if not ev:
        raise ValueError("Event not found")

    google_conn = GoogleConnectionRepository().get_by_user_id(user_id)
    if not is_google_configured() or not google_conn:
        rem_repo.update_google_sync(
            reminder_id,
            user_id,
            sync_status="not_connected",
            google_event_id=rem.google_event_id,
            sync_error="Google account is not connected",
        )
        return rem_repo.get_by_id(reminder_id, user_id)

    try:
        google_event_id = google_calendar_service.create_event(user_id, ev, rem)
        rem_repo.update_google_sync(
            reminder_id,
            user_id,
            sync_status="synced",
            google_event_id=google_event_id,
            sync_error=None,
        )
    except Exception as e:
        logger.exception("Failed to sync reminder %s to Google Calendar: %s", reminder_id, e)
        still_conn = GoogleConnectionRepository().get_by_user_id(user_id)
        status_val = "not_connected" if not still_conn else "failed"
        rem_repo.update_google_sync(
            reminder_id,
            user_id,
            sync_status=status_val,
            google_event_id=rem.google_event_id,
            sync_error=str(e)[:200],
        )

    return rem_repo.get_by_id(reminder_id, user_id)


def check_and_send_due(user_id: int) -> CheckResult:
    """Check for due reminders and send them.

    Args:
        user_id: The user ID.

    Returns:
        CheckResult with counts, errors, and details.
    """
    import os
    from app.utils import config

    username = os.environ.get("EMAIL_USERNAME", getattr(config, "EMAIL_USERNAME", ""))
    password = os.environ.get("EMAIL_APP_PASSWORD", getattr(config, "EMAIL_APP_PASSWORD", ""))

    rem_repo = ReminderRepository()
    now = datetime.now().isoformat()
    due = rem_repo.due_scheduled(user_id, now)

    # If email is not configured (EMAIL_USERNAME or EMAIL_APP_PASSWORD empty):
    # do NOT attempt sending and do NOT mark any reminder failed
    if not username or not password:
        return CheckResult(
            configured=False,
            sent=0,
            failed=0,
            skipped=len(due),
            errors=["Email is not set up. Add EMAIL_USERNAME and EMAIL_APP_PASSWORD to the .env file."],
            details=[],
        )

    if not due:
        return CheckResult(
            configured=True,
            sent=0,
            failed=0,
            skipped=0,
            errors=[],
            details=[],
        )

    user_repo = UserRepository()
    user = user_repo.get_by_id(user_id)
    user_email = (user.email or "").strip() if user else ""

    sent = 0
    failed = 0
    skipped = 0
    errors: List[str] = []
    details: List[Tuple[int, bool, str]] = []

    for r in due:
        try:
            ok, detail = email_service.send_reminder_email(
                r.subject or "",
                r.body or "",
                to_address=user_email or None,
            )
            if ok:
                rem_repo.set_status(r.id, user_id, "sent", datetime.now().isoformat())
                sent += 1
                details.append((r.id, True, "sent"))
            else:
                rem_repo.set_status(r.id, user_id, "failed")
                failed += 1
                err_msg = detail.strip()[:200]
                errors.append(err_msg)
                details.append((r.id, False, detail))
        except Exception as e:
            rem_repo.set_status(r.id, user_id, "failed")
            failed += 1
            logger.exception("Failed to send reminder %s", r.id)
            err_msg = f"Send failed: {str(e).strip()[:200]}"
            errors.append(err_msg)
            details.append((r.id, False, f"Exception: {e}"))

    return CheckResult(
        configured=True,
        sent=sent,
        failed=failed,
        skipped=skipped,
        errors=errors,
        details=details,
    )