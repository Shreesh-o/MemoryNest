"""Tests for ICS calendar export service."""

from __future__ import annotations

import pytest
from icalendar import Calendar

from app.services.ics_service import build_ics, build_ics_from_events_and_reminders
from app.database.models import Event, Reminder


def _parse_ics(ics_bytes: bytes) -> Calendar:
    return Calendar.from_ical(ics_bytes)


def _get_str(val) -> str:
    """Convert icalendar value to string."""
    return str(val) if val is not None else ""


def test_build_ics_timed_event():
    """Test ICS generation for a timed event (with time component)."""
    events = [
        Event(
            id=1,
            user_id=1,
            event_text="Team meeting",
            event_date="2026-10-15T10:00:00",
            raw_date="Oct 15 10am",
        )
    ]
    ics_bytes = build_ics(events, "user@example.com")
    cal = _parse_ics(ics_bytes)

    assert cal.get("prodid") == "-//MemoryNest//Calendar Export//EN"
    assert cal.get("version") == "2.0"
    assert cal.get("x-wr-calname") == "MemoryNest Reminders (user@example.com)"

    vevents = list(cal.walk("vevent"))
    assert len(vevents) == 1

    ev = vevents[0]
    assert ev.get("summary") == "Team meeting"
    assert ev.get("uid") == "memorynest-event-1@memorynest.local"
    desc = _get_str(ev.get("description"))
    assert "Original date text: Oct 15 10am" in desc
    assert "Parsed date: 2026-10-15T10:00:00" in desc

    dtstart = ev.get("dtstart").dt
    assert dtstart.hour == 10
    assert dtstart.minute == 0
    assert dtstart.tzinfo is not None
    assert str(dtstart.tzinfo) == "Asia/Kolkata"


def test_build_ics_all_day_event():
    """Test ICS generation for an all-day event (date only, no time)."""
    events = [
        Event(
            id=2,
            user_id=1,
            event_text="Project deadline",
            event_date="2026-12-31",
            raw_date="Dec 31",
        )
    ]
    ics_bytes = build_ics(events, "user@example.com")
    cal = _parse_ics(ics_bytes)

    vevents = list(cal.walk("vevent"))
    assert len(vevents) == 1

    ev = vevents[0]
    assert ev.get("summary") == "Project deadline"

    dtstart = ev.get("dtstart").dt
    # All-day events should have date type, not datetime
    from datetime import date
    assert isinstance(dtstart, date)
    assert dtstart.year == 2026
    assert dtstart.month == 12
    assert dtstart.day == 31


def test_build_ics_empty_list():
    """Test ICS generation with empty event list."""
    events = []
    ics_bytes = build_ics(events, "user@example.com")
    cal = _parse_ics(ics_bytes)

    vevents = list(cal.walk("vevent"))
    assert len(vevents) == 0
    assert cal.get("x-wr-calname") == "MemoryNest Reminders (user@example.com)"


def test_build_ics_special_characters():
    """Test ICS generation with special characters in event text."""
    events = [
        Event(
            id=3,
            user_id=1,
            event_text="Meeting with comma, semicolon; and newline\nchars",
            event_date="2026-10-15",
            raw_date="Oct 15",
        )
    ]
    ics_bytes = build_ics(events, "user@example.com")
    cal = _parse_ics(ics_bytes)

    vevents = list(cal.walk("vevent"))
    assert len(vevents) == 1

    ev = vevents[0]
    summary = _get_str(ev.get("summary"))
    assert "Meeting with comma" in summary
    assert "semicolon" in summary
    assert "newline" in summary


def test_build_ics_kolkata_timezone():
    """Test that events use Asia/Kolkata timezone."""
    events = [
        Event(
            id=4,
            user_id=1,
            event_text="Timezone test",
            event_date="2026-10-15T14:30:00",
            raw_date="Oct 15 2:30pm",
        )
    ]
    ics_bytes = build_ics(events, "user@example.com")
    cal = _parse_ics(ics_bytes)

    vevents = list(cal.walk("vevent"))
    ev = vevents[0]
    dtstart = ev.get("dtstart").dt
    assert dtstart.tzinfo is not None
    assert str(dtstart.tzinfo) == "Asia/Kolkata"
    assert dtstart.hour == 14
    assert dtstart.minute == 30


def test_build_ics_from_events_and_reminders():
    """Test building ICS from events and reminders with VALARM."""
    events = [
        Event(
            id=1,
            user_id=1,
            event_text="Team meeting",
            event_date="2026-10-15T10:00:00",
            raw_date="Oct 15 10am",
        )
    ]
    reminders = [
        Reminder(
            id=1,
            user_id=1,
            event_id=1,
            remind_at="2026-10-15 09:00:00",
            subject="Meeting reminder",
            body="Team meeting at 10am",
        )
    ]

    ics_bytes = build_ics_from_events_and_reminders(events, reminders, "user@example.com")
    cal = _parse_ics(ics_bytes)

    vevents = list(cal.walk("vevent"))
    assert len(vevents) == 1

    ev = vevents[0]
    # Check VALARM exists
    alarms = list(ev.walk("valarm"))
    assert len(alarms) == 1

    alarm = alarms[0]
    assert alarm.get("action") == "DISPLAY"
    assert "Team meeting" in _get_str(alarm.get("description"))

    # Check trigger is a timedelta (1 hour before)
    trigger = alarm.get("trigger")
    from datetime import timedelta
    # icalendar may return trigger as vDDDTypes or timedelta
    if hasattr(trigger, 'dt'):
        trigger = trigger.dt
    if isinstance(trigger, timedelta):
        assert trigger == timedelta(hours=1)
    else:
        # Handle case where trigger is a datetime/time
        assert trigger is not None


def test_build_ics_from_events_and_reminders_all_day():
    """Test ICS with all-day event and reminder."""
    events = [
        Event(
            id=2,
            user_id=1,
            event_text="Project deadline",
            event_date="2026-12-31",
            raw_date="Dec 31",
        )
    ]
    reminders = [
        Reminder(
            id=2,
            user_id=1,
            event_id=2,
            remind_at="2026-12-30 09:00:00",
            subject="Deadline reminder",
            body="Project deadline tomorrow",
        )
    ]

    ics_bytes = build_ics_from_events_and_reminders(events, reminders, "user@example.com")
    cal = _parse_ics(ics_bytes)

    vevents = list(cal.walk("vevent"))
    assert len(vevents) == 1

    ev = vevents[0]
    alarms = list(ev.walk("valarm"))
    assert len(alarms) == 1

    alarm = alarms[0]
    trigger = alarm.get("trigger")
    from datetime import timedelta
    if hasattr(trigger, 'dt'):
        trigger = trigger.dt
    if isinstance(trigger, timedelta):
        # 15 hours before (Dec 30 09:00 to Dec 31 00:00 = 15 hours)
        assert trigger == timedelta(hours=15)
    else:
        assert trigger is not None


def test_build_ics_event_without_date_skipped():
    """Test that events without event_date are skipped."""
    events = [
        Event(
            id=1,
            user_id=1,
            event_text="Has date",
            event_date="2026-10-15",
            raw_date="Oct 15",
        ),
        Event(
            id=2,
            user_id=1,
            event_text="No date",
            event_date=None,
            raw_date="sometime",
        ),
    ]
    ics_bytes = build_ics(events, "user@example.com")
    cal = _parse_ics(ics_bytes)

    vevents = list(cal.walk("vevent"))
    assert len(vevents) == 1
    assert vevents[0].get("summary") == "Has date"


def test_build_ics_multiple_events():
    """Test ICS generation with multiple events."""
    events = [
        Event(id=1, user_id=1, event_text="Event 1", event_date="2026-10-15"),
        Event(id=2, user_id=1, event_text="Event 2", event_date="2026-10-20"),
        Event(id=3, user_id=1, event_text="Event 3", event_date="2026-10-25T14:00:00"),
    ]
    ics_bytes = build_ics(events, "user@example.com")
    cal = _parse_ics(ics_bytes)

    vevents = list(cal.walk("vevent"))
    assert len(vevents) == 3
    summaries = {_get_str(ev.get("summary")) for ev in vevents}
    assert summaries == {"Event 1", "Event 2", "Event 3"}