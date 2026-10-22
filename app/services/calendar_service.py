"""Calendar service: query and aggregate events and reminders for calendar views."""

from __future__ import annotations

from datetime import datetime
from typing import List

from app.api.schemas import CalendarItem
from app.database.repositories import EventRepository, ReminderRepository


def get_calendar_items(user_id: int, start: str, end: str) -> List[CalendarItem]:
    """Return calendar items for the user within a validated date range (max 62 days).

    Args:
        user_id: Current logged-in user ID.
        start: Start date string in YYYY-MM-DD format.
        end: End date string in YYYY-MM-DD format.

    Returns:
        List of CalendarItem dicts sorted chronologically by date.

    Raises:
        ValueError: On invalid date format, invalid range (start > end), or range > 62 days.
    """
    if not start or not end:
        raise ValueError("start and end date parameters are required")

    try:
        dt_start = datetime.strptime(start, "%Y-%m-%d").date()
        dt_end = datetime.strptime(end, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        raise ValueError("Invalid date format; expected YYYY-MM-DD")

    if dt_start > dt_end:
        raise ValueError("start date must be before or equal to end date")

    if (dt_end - dt_start).days > 62:
        raise ValueError("Date range exceeds maximum of 62 days")

    ev_repo = EventRepository()
    rem_repo = ReminderRepository()

    # Query events: include 'pending' and 'confirmed' (not 'skipped')
    events = ev_repo.list_in_date_range(
        user_id=user_id,
        start_date=start,
        end_date=end,
        statuses=["pending", "confirmed"],
    )

    # Query reminders: include 'scheduled' and 'sent' (not 'cancelled')
    reminders = rem_repo.list_in_date_range(
        user_id=user_id,
        start_date=start,
        end_date=end,
        statuses=["scheduled", "sent"],
    )

    items: List[CalendarItem] = []

    # Map events
    event_doc_map = {}
    for ev in events:
        if not ev.event_date:
            continue
        event_doc_map[ev.id] = ev.document_id
        is_all_day = "T" not in ev.event_date and ":" not in ev.event_date
        items.append(
            CalendarItem(
                id=ev.id,
                kind="event",
                title=ev.event_text,
                date=ev.event_date,
                all_day=is_all_day,
                status=ev.status,
                document_id=ev.document_id,
                event_id=ev.id,
            )
        )

    # Map reminders
    for r in reminders:
        doc_id = event_doc_map.get(r.event_id)
        if doc_id is None:
            ev = ev_repo.get_by_id(r.event_id, user_id)
            if ev:
                doc_id = ev.document_id
                event_doc_map[r.event_id] = doc_id

        items.append(
            CalendarItem(
                id=r.id,
                kind="reminder",
                title=r.subject or "Reminder",
                date=r.remind_at,
                all_day=False,
                status=r.status,
                document_id=doc_id,
                event_id=r.event_id,
            )
        )

    # Sort items chronologically by date string, then kind
    items.sort(key=lambda x: (x.date, 0 if x.kind == "event" else 1, x.id))
    return items
