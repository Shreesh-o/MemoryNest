"""ICS calendar export service using icalendar library."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import pytz
from icalendar import Calendar, Event as ICalEvent, Alarm

from app.database.models import Event, Reminder


KOLKATA_TZ = pytz.timezone("Asia/Kolkata")


def _to_kolkata(dt_str: str, is_all_day: bool) -> datetime:
    """Parse ISO date/datetime string and localize to Asia/Kolkata."""
    if is_all_day:
        return KOLKATA_TZ.localize(datetime.strptime(dt_str, "%Y-%m-%d"))
    dt = datetime.fromisoformat(dt_str)
    if dt.tzinfo is None:
        return KOLKATA_TZ.localize(dt)
    return dt.astimezone(KOLKATA_TZ)


def _make_uid(event_id: int, prefix: str = "memorynest") -> str:
    """Generate a stable UID for the event."""
    return f"{prefix}-event-{event_id}@memorynest.local"


def build_ics(events: list[Event], user_email: Optional[str] = None) -> bytes:
    """Build an ICS calendar from a list of Event objects.

    Args:
        events: List of Event objects with optional linked Reminder.
        user_email: Optional organizer email.

    Returns:
        ICS calendar as bytes.
    """
    cal = Calendar()
    cal.add("prodid", "-//MemoryNest//Calendar Export//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    if user_email:
        cal.add("x-wr-calname", f"MemoryNest Reminders ({user_email})")
    else:
        cal.add("x-wr-calname", "MemoryNest Reminders")

    dtstamp = datetime.now(timezone.utc)

    for ev in events:
        ical_event = ICalEvent()
        ical_event.add("uid", _make_uid(ev.id))
        ical_event.add("dtstamp", dtstamp)
        ical_event.add("summary", ev.event_text or "Untitled Event")

        # Description with source document info
        desc_parts = []
        if ev.raw_date:
            desc_parts.append(f"Original date text: {ev.raw_date}")
        if ev.document_id:
            desc_parts.append(f"Source document ID: {ev.document_id}")
        if ev.event_date:
            desc_parts.append(f"Parsed date: {ev.event_date}")
        ical_event.add("description", "\n".join(desc_parts) if desc_parts else "")

        # Determine if all-day event (only date, no time)
        is_all_day = ev.event_date is not None and "T" not in ev.event_date and ":" not in ev.event_date

        if ev.event_date:
            dtstart = _to_kolkata(ev.event_date, is_all_day)
            ical_event.add("dtstart", dtstart)
            if not is_all_day:
                ical_event.add("dtend", dtstart + timedelta(hours=1))
        else:
            continue

        # Add VALARM if there's a linked reminder with remind_at
        if hasattr(ev, "reminder") and ev.reminder and ev.reminder.remind_at:
            alarm = Alarm()
            alarm.add("action", "DISPLAY")
            alarm.add("description", f"Reminder: {ev.event_text}")

            remind_dt = datetime.fromisoformat(ev.reminder.remind_at)
            if remind_dt.tzinfo is None:
                remind_dt = KOLKATA_TZ.localize(remind_dt)
            else:
                remind_dt = remind_dt.astimezone(KOLKATA_TZ)

            # Calculate trigger as relative to event start
            if ev.event_date:
                event_dt = _to_kolkata(ev.event_date, is_all_day)
                diff = event_dt - remind_dt
                trigger_delta = diff if diff.total_seconds() > 0 else timedelta(0)
                alarm.add("trigger", trigger_delta)
            else:
                alarm.add("trigger", timedelta(0))

            ical_event.add_component(alarm)

        cal.add_component(ical_event)

    return cal.to_ical()


def build_ics_from_events_and_reminders(
    events: list[Event],
    reminders: list[Reminder],
    user_email: Optional[str] = None,
) -> bytes:
    """Build ICS from events and their reminders.

    Matches reminders to events by event_id.
    """
    reminder_map = {r.event_id: r for r in reminders}

    for ev in events:
        if ev.id in reminder_map:
            ev.reminder = reminder_map[ev.id]

    return build_ics(events, user_email)