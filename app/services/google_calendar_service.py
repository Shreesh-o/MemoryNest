"""Google Calendar service: create, update, and delete Google Calendar events."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Optional
import pytz
from google.auth.exceptions import RefreshError

from app.database.models import Event, Reminder
from app.database.repositories import DocumentRepository, GoogleConnectionRepository
from app.services.google_auth_service import get_calendar_client

logger = logging.getLogger(__name__)

KOLKATA_TZ = pytz.timezone("Asia/Kolkata")
GOOGLE_MIN_REMINDER_MINUTES = 0
GOOGLE_MAX_REMINDER_MINUTES = 40320  # 4 weeks in minutes


def _parse_event_datetime(event_date: Optional[str], is_all_day: bool) -> tuple[datetime, bool]:
    """Parse event_date string into a localized datetime.

    For all-day events, returns localized midnight Asia/Kolkata.
    """
    if not event_date:
        now = datetime.now(KOLKATA_TZ)
        return now, False

    if is_all_day:
        dt = datetime.strptime(event_date[:10], "%Y-%m-%d")
        return KOLKATA_TZ.localize(dt), True

    clean = event_date.replace(" ", "T")
    dt = datetime.fromisoformat(clean)
    if dt.tzinfo is None:
        return KOLKATA_TZ.localize(dt), False
    return dt.astimezone(KOLKATA_TZ), False


def _parse_remind_datetime(remind_at: str) -> datetime:
    """Parse remind_at string and localize to Asia/Kolkata."""
    clean = remind_at.replace(" ", "T")
    dt = datetime.fromisoformat(clean)
    if dt.tzinfo is None:
        return KOLKATA_TZ.localize(dt)
    return dt.astimezone(KOLKATA_TZ)


def _execute_with_retry(user_id: int, operation: Callable[[Any], Any]) -> Any:
    """Execute a Google Calendar API operation with retry on 401/auth errors.

    If 401 Unauthorized or token revocation occurs:
    - Attempt refresh and retry operation once.
    - If retry fails or token is revoked, marks the user's connection as disconnected.
    """
    service = get_calendar_client(user_id)
    if service is None:
        raise RuntimeError("Google Calendar client unavailable or user not connected")

    try:
        return operation(service)
    except Exception as exc:
        is_auth_error = False
        status_code = getattr(getattr(exc, "resp", None), "status", None)
        if status_code == 401:
            is_auth_error = True
        elif isinstance(exc, RefreshError) or "invalid_grant" in str(exc).lower() or "401" in str(exc):
            is_auth_error = True

        if is_auth_error:
            logger.warning("Google Calendar auth error (401/revoked) for user_id=%s. Attempting retry...", user_id)
            try:
                refreshed_service = get_calendar_client(user_id)
                if refreshed_service is not None:
                    return operation(refreshed_service)
            except Exception as retry_err:
                logger.warning("Retry failed for user_id=%s: %s", user_id, retry_err)

            # Token is revoked or refresh failed; mark connection as disconnected
            logger.warning("Marking user_id=%s as disconnected from Google", user_id)
            GoogleConnectionRepository().delete_by_user_id(user_id)
            raise RuntimeError(f"Google authorization failed (marked disconnected): {exc}") from exc

        raise exc


def build_event_body(user_id: int, event: Event, reminder: Reminder) -> dict[str, Any]:
    """Build the Google Calendar event dictionary."""
    # Summary (Title) = event text
    summary = event.event_text

    # Description = document name + "Created by MemoryNest"
    doc_name: Optional[str] = None
    if event.document_id:
        doc = DocumentRepository().get_by_id(event.document_id, user_id)
        if doc:
            doc_name = doc.filename

    if doc_name:
        description = f"{doc_name}\nCreated by MemoryNest"
    else:
        description = "Created by MemoryNest"

    # Determine if all-day event (date only, no time components)
    is_all_day = (
        event.event_date is not None
        and "T" not in event.event_date
        and ":" not in event.event_date
    )

    event_dt, is_all_day = _parse_event_datetime(event.event_date, is_all_day)
    remind_dt = _parse_remind_datetime(reminder.remind_at)

    # Popup reminder matching remind_at (minutes before event start, clamped to Google's limits [0, 40320])
    diff_minutes = int(round((event_dt - remind_dt).total_seconds() / 60.0))
    clamped_minutes = max(GOOGLE_MIN_REMINDER_MINUTES, min(GOOGLE_MAX_REMINDER_MINUTES, diff_minutes))

    body: dict[str, Any] = {
        "summary": summary,
        "description": description,
        "reminders": {
            "useDefault": False,
            "overrides": [{"method": "popup", "minutes": clamped_minutes}],
        },
    }

    if is_all_day:
        start_date_str = event_dt.strftime("%Y-%m-%d")
        end_date_str = (event_dt + timedelta(days=1)).strftime("%Y-%m-%d")
        body["start"] = {"date": start_date_str}
        body["end"] = {"date": end_date_str}
    else:
        start_dt_str = event_dt.isoformat()
        end_dt_str = (event_dt + timedelta(hours=1)).isoformat()
        body["start"] = {
            "dateTime": start_dt_str,
            "timeZone": "Asia/Kolkata",
        }
        body["end"] = {
            "dateTime": end_dt_str,
            "timeZone": "Asia/Kolkata",
        }

    return body


def create_event(user_id: int, event: Event, reminder: Reminder) -> str:
    """Create or update a Google Calendar event.

    Idempotent: if reminder.google_event_id is present, updates the existing event.
    Returns the google_event_id.
    """
    body = build_event_body(user_id, event, reminder)

    if reminder.google_event_id:
        try:
            _execute_with_retry(
                user_id,
                lambda svc: svc.events().update(
                    calendarId="primary",
                    eventId=reminder.google_event_id,
                    body=body,
                ).execute(),
            )
            return reminder.google_event_id
        except Exception as exc:
            status_code = getattr(getattr(exc, "resp", None), "status", None)
            if status_code == 404:
                # Event was deleted remotely; create a new one
                res = _execute_with_retry(
                    user_id,
                    lambda svc: svc.events().insert(
                        calendarId="primary",
                        body=body,
                    ).execute(),
                )
                new_id = res.get("id")
                if not new_id:
                    raise RuntimeError("Google API did not return an event ID on recreate")
                return str(new_id)
            raise exc

    res = _execute_with_retry(
        user_id,
        lambda svc: svc.events().insert(
            calendarId="primary",
            body=body,
        ).execute(),
    )
    google_event_id = res.get("id")
    if not google_event_id:
        raise RuntimeError("Google API did not return an event ID")
    return str(google_event_id)


def delete_event(user_id: int, google_event_id: str) -> None:
    """Delete a Google Calendar event by google_event_id."""
    if not google_event_id:
        return

    def _delete(svc):
        try:
            svc.events().delete(calendarId="primary", eventId=google_event_id).execute()
        except Exception as exc:
            status_code = getattr(getattr(exc, "resp", None), "status", None)
            if status_code in (404, 410):
                # Event already deleted
                return
            raise exc

    _execute_with_retry(user_id, _delete)
