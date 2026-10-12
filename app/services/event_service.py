"""Date/event extraction from document text: regex + dateparser first, LLM fallback."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import List, Optional

import dateparser

from app.services import llm_service

logger = logging.getLogger(__name__)

_DATE_REGEXES = [
    # ISO and common formats
    r"\b\d{4}-\d{2}-\d{2}\b",                    # 2026-10-15
    r"\b\d{1,2}/\d{1,2}/\d{4}\b",                # 10/15/2026
    r"\b\d{1,2}-\d{1,2}-\d{4}\b",                # 15-10-2026
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b",  # Oct 15, 2026
    r"\b\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}\b",  # 15 Oct 2026
    r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2},? \d{4}\b",
    # Ordinal formats: 26th October, 5th Nov
    r"\b\d{1,2}(?:st|nd|rd|th) (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*(?:uary|uary|ruary|ch|il|ust|ember|ember|ember)?\b",
    r"\b\d{1,2}(?:st|nd|rd|th) (?:January|February|March|April|May|June|July|August|September|October|November|December)\b",
    # Month + day without year: October 30, Oct 15
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2}\b",
    r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}\b",
    # Relative dates
    r"\b(?:tomorrow|today|next week|next month|next year|yesterday)\b",
]

_COMPILED_REGEXES = [re.compile(rx, re.IGNORECASE) for rx in _DATE_REGEXES]

# Dateparser settings for Indian date formats
dateparser_settings = {
    "DATE_ORDER": "DMY",
    "PREFER_DATES_FROM": "future",
    "TIMEZONE": "Asia/Kolkata",
}


def _get_relative_base() -> datetime:
    return datetime.now()


def _parse_date(raw: str) -> Optional[datetime]:
    """Parse a date string using dateparser with appropriate settings.

    For ISO dates (YYYY-MM-DD), DATE_ORDER doesn't affect them.
    For slash dates (DM/YM), DMY ordering is needed for Indian format.
    For month+day without year, dateparser infers the year.
    For relative dates, RELATIVE_BASE is set to now.
    """
    # Check if it's an ISO date (YYYY-MM-DD) - don't use DATE_ORDER for these
    if re.match(r"^\d{4}-\d{1,2}-\d{1,2}$", raw):
        parsed = dateparser.parse(raw, languages=["en"], settings={
            "PREFER_DATES_FROM": "future",
            "TIMEZONE": "Asia/Kolkata",
        })
    else:
        parsed = dateparser.parse(raw, languages=["en"], settings=dateparser_settings)
    return parsed


def _is_past_date(parsed: datetime) -> bool:
    """Check if a parsed date is in the past (relative to now)."""
    now = datetime.now()
    return parsed < now


def _extract_with_regex(text: str) -> List[dict]:
    """Find date-like spans in text using regex, parse with dateparser."""
    events = []
    sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
    logger.info("Event extraction: %d chars, %d candidate lines", len(text), len(sentences))

    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        for rx in _COMPILED_REGEXES:
            for m in rx.finditer(sent):
                raw = m.group(0)
                parsed = _parse_date(raw)
                if parsed:
                    if _is_past_date(parsed):
                        logger.info("Dropped past date: %s -> %s (before today)", raw, parsed.date().isoformat())
                        continue
                    events.append(
                        {
                            "event_text": sent[:500],
                            "event_date": parsed.date().isoformat(),
                            "raw_date": raw,
                        }
                    )
                    break  # one date per sentence is enough
            if events and events[-1]["event_text"] == sent[:500]:
                break
    logger.info("Regex extraction found %d events", len(events))
    return events


def _extract_with_llm(text: str) -> List[dict]:
    """Fallback: ask LLM to extract events as JSON."""
    prompt = (
        "Extract any dated events or deadlines from the following text. "
        "Return a JSON array of objects with keys: "
        "'event_text' (the sentence containing the event), "
        "'event_date' (ISO format YYYY-MM-DD or null), "
        "'raw_date' (the date phrase as it appears). "
        "Only include items that have a clear date. If none, return empty array.\n\n"
        f"Text:\n{text[:4000]}"
    )
    try:
        resp = llm_service.generate(prompt, system="You extract structured data. Output JSON only.", temperature=0.0)
        data = json.loads(resp)
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def extract_events(text: str) -> List[dict]:
    """Main entry: regex first, LLM fallback if nothing found."""
    events = _extract_with_regex(text)
    if not events:
        events = _extract_with_llm(text)
    # Deduplicate by (event_text, event_date)
    seen = set()
    uniq = []
    for e in events:
        key = (e.get("event_text", "")[:100], e.get("event_date"))
        if key not in seen:
            seen.add(key)
            uniq.append(e)
    return uniq
