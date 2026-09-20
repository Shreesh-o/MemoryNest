"""Date/event extraction from document text: regex + dateparser first, LLM fallback."""

from __future__ import annotations

import json
import re
from typing import List, Optional

import dateparser

from app.services import llm_service

_DATE_REGEXES = [
    # ISO and common formats
    r"\b\d{4}-\d{2}-\d{2}\b",                    # 2026-10-15
    r"\b\d{1,2}/\d{1,2}/\d{4}\b",                # 10/15/2026
    r"\b\d{1,2}-\d{1,2}-\d{4}\b",                # 15-10-2026
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b",  # Oct 15, 2026
    r"\b\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}\b",  # 15 Oct 2026
    r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2},? \d{4}\b",
    # Relative/worded dates (dateparser handles these)
]

_COMPILED_REGEXES = [re.compile(rx, re.IGNORECASE) for rx in _DATE_REGEXES]


def _extract_with_regex(text: str) -> List[dict]:
    """Find date-like spans in text using regex, parse with dateparser."""
    events = []
    sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        for rx in _COMPILED_REGEXES:
            for m in rx.finditer(sent):
                raw = m.group(0)
                parsed = dateparser.parse(raw, languages=["en"])
                if parsed:
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