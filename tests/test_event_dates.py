"""Tests for event extraction date handling (past-date filtering, relative dates, fixed clock)."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.services import event_service


def test_event_today_is_kept():
    """A deadline dated today is kept (not filtered as past)."""
    now = datetime(2026, 10, 15, 10, 0)
    text = "Submission deadline: 15 October 2026"
    events = event_service.extract_events(text, now=now)
    assert len(events) == 1
    assert events[0]["event_date"] == "2026-10-15"


def test_event_yesterday_is_dropped():
    """A deadline dated yesterday is dropped (filtered as past)."""
    now = datetime(2026, 10, 16, 10, 0)
    text = "Submission deadline: 15 October 2026"
    events = event_service.extract_events(text, now=now)
    assert len(events) == 0


def test_tomorrow_resolves_from_now():
    """Relative 'tomorrow' resolves from the fixed `now` passed in."""
    now = datetime(2026, 10, 12, 10, 0)
    text = "Meeting tomorrow at 5 pm"
    events = event_service.extract_events(text, now=now)
    assert len(events) == 1
    assert events[0]["event_date"] == "2026-10-13"


def test_indian_date_formats_with_fixed_now():
    """Formats like '5th Nov' and '25/10/2026' parse correctly with a fixed clock."""
    now = datetime(2026, 10, 12, 10, 0)
    text = "Fee payment last date - 5th Nov\nExam: 25/10/2026"
    events = event_service.extract_events(text, now=now)
    dates = {e["event_date"] for e in events}
    assert "2026-11-05" in dates
    assert "2026-10-25" in dates


def test_relative_base_used_for_parsing():
    """RELATIVE_BASE affects parsing of relative dates like 'next week'."""
    now = datetime(2026, 10, 12, 10, 0)
    text = "Review next week"
    events = event_service.extract_events(text, now=now)
    # "next week" from 2026-10-12 should be around 2026-10-19
    assert len(events) >= 1
    parsed = events[0]["event_date"]
    # Should be in the week after 2026-10-12
    assert "2026-10-19" <= parsed <= "2026-10-25"


def test_iso_date_parsing_unaffected_by_dmy():
    """ISO dates (YYYY-MM-DD) parse correctly regardless of DATE_ORDER."""
    now = datetime(2026, 10, 12, 10, 0)
    text = "Event on 2026-10-20"
    events = event_service.extract_events(text, now=now)
    assert len(events) == 1
    assert events[0]["event_date"] == "2026-10-20"


def test_slash_date_dmy_parsing():
    """Slash dates parse as DD/MM/YYYY with DMY setting."""
    now = datetime(2026, 10, 12, 10, 0)
    text = "Exam on 25/10/2026"
    events = event_service.extract_events(text, now=now)
    assert len(events) == 1
    assert events[0]["event_date"] == "2026-10-25"


def test_ordinal_date_parsing():
    """Ordinal dates like '26th October' parse correctly."""
    now = datetime(2026, 10, 12, 10, 0)
    text = "Viva on Monday 26th October"
    events = event_service.extract_events(text, now=now)
    assert len(events) == 1
    assert events[0]["event_date"] == "2026-10-26"


def test_month_name_partial_parsing():
    """Partial month names like 'Oct 30' parse correctly."""
    now = datetime(2026, 10, 12, 10, 0)
    text = "Assignment submission by October 30"
    events = event_service.extract_events(text, now=now)
    assert len(events) == 1
    assert events[0]["event_date"] == "2026-10-30"