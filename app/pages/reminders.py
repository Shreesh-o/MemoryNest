"""Reminders page — extracted dates/events, confirmation, email reminders, .ics export."""

from __future__ import annotations

import streamlit as st
from datetime import datetime

from app.database.repositories import DocumentRepository, EventRepository, ReminderRepository
from app.services import event_service, email_service, ics_service
from app.utils.config import RAG_MIN_SIMILARITY


def _get_confirmed_events_with_reminders(ev_repo, rem_repo, user_id):
    """Get confirmed events with their reminders for .ics export."""
    events = ev_repo.list_for_user(user_id, status="confirmed")
    if not events:
        return [], []
    reminders = rem_repo.list_for_user(user_id, status="scheduled")
    # Filter reminders to only those for confirmed events
    confirmed_event_ids = {e.id for e in events}
    reminders = [r for r in reminders if r.event_id in confirmed_event_ids]
    return events, reminders


def _get_scheduled_reminders_with_events(ev_repo, rem_repo, user_id):
    """Get scheduled reminders with their events for .ics export."""
    reminders = rem_repo.list_for_user(user_id, status="scheduled")
    if not reminders:
        return [], []
    event_ids = {r.event_id for r in reminders}
    events = [ev_repo.get_by_id(eid, user_id) for eid in event_ids]
    events = [e for e in events if e is not None]
    return events, reminders


def render() -> None:
    user = st.session_state.user
    st.header("⏰ Reminders & Events")

    doc_repo = DocumentRepository()
    ev_repo = EventRepository()
    rem_repo = ReminderRepository()

    # Tab 1: Extract events from documents
    tab_extract, tab_pending, tab_scheduled = st.tabs(
        ["Extract from docs", "Pending confirmation", "Scheduled reminders"]
    )

    with tab_extract:
        st.subheader("Extract dates from a document")
        docs = [d for d in doc_repo.list_for_user(user.id) if d.status == "ready"]
        if not docs:
            st.info("No ready documents")
        else:
            doc_map = {f"{d.filename}": d for d in docs}
            sel = st.selectbox("Document", list(doc_map.keys()))
            doc = doc_map[sel]
            if st.button("Extract events"):
                with st.spinner("Analyzing document..."):
                    text = doc.text_preview or ""
                    if not text:
                        st.warning("Document has no text preview")
                    else:
                        try:
                            events = event_service.extract_events(text)
                            if not events:
                                st.info("No events found")
                            else:
                                for e in events:
                                    ev = ev_repo.create(
                                        user_id=user.id,
                                        event_text=e["event_text"],
                                        document_id=doc.id,
                                        event_date=e.get("event_date"),
                                        raw_date=e.get("raw_date"),
                                    )
                                st.success(f"Extracted {len(events)} event(s)")
                                st.rerun()
                        except Exception as e:
                            import logging
                            logging.exception("Event extraction failed for doc %s", doc.id)
                            st.error(f"Extraction failed: {e}")

    with tab_pending:
        st.subheader("Events awaiting confirmation")
        pending = ev_repo.list_for_user(user.id, status="pending")
        if not pending:
            st.info("No pending events")
        else:
            for e in pending:
                with st.expander(f"{e.raw_date or 'No date'} — {e.event_text[:80]}"):
                    st.write(e.event_text)
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("Confirm", key=f"conf_{e.id}"):
                            try:
                                ev_repo.set_status(e.id, user.id, "confirmed")
                                if e.event_date:
                                    remind_at = f"{e.event_date} 09:00:00"
                                else:
                                    remind_at = datetime.now().strftime("%Y-%m-%d 09:00:00")
                                rem_repo.create(
                                    user_id=user.id,
                                    event_id=e.id,
                                    remind_at=remind_at,
                                    subject=f"Reminder: {e.event_text[:60]}",
                                    body=f"Event: {e.event_text}\nDate: {e.event_date or 'TBD'}\nRaw: {e.raw_date or 'N/A'}",
                                )
                                st.success("Confirmed and reminder scheduled")
                                st.rerun()
                            except Exception as exc:
                                import logging
                                logging.exception("Confirm event failed for event %s", e.id)
                                st.error(f"Confirm failed: {exc}")
                    with col2:
                        if st.button("Skip", key=f"skip_{e.id}"):
                            ev_repo.set_status(e.id, user.id, "skipped")
                            st.rerun()
                    with col3:
                        if st.button("Delete", key=f"del_ev_{e.id}", type="secondary"):
                            ev_repo.delete(e.id, user.id)
                            st.rerun()

        # .ics export for all confirmed events
        st.divider()
        st.subheader("Export to calendar")
        confirmed_events, confirmed_reminders = _get_confirmed_events_with_reminders(ev_repo, rem_repo, user.id)
        if confirmed_events:
            ics_data = ics_service.build_ics_from_events_and_reminders(
                confirmed_events, confirmed_reminders, user.email
            )
            st.download_button(
                label="📅 Download all confirmed events (.ics)",
                data=ics_data,
                file_name="memorynest_confirmed_events.ics",
                mime="text/calendar",
            )
        else:
            st.info("No confirmed events to export")

    with tab_scheduled:
        st.subheader("Scheduled reminders")
        reminders = rem_repo.list_for_user(user.id, status="scheduled")
        if not reminders:
            st.info("No scheduled reminders")
        else:
            # Bulk export for all scheduled
            scheduled_events, scheduled_reminders = _get_scheduled_reminders_with_events(ev_repo, rem_repo, user.id)
            if scheduled_events:
                ics_data = ics_service.build_ics_from_events_and_reminders(
                    scheduled_events, scheduled_reminders, user.email
                )
                st.download_button(
                    label="📅 Download all scheduled reminders (.ics)",
                    data=ics_data,
                    file_name="memorynest_scheduled_reminders.ics",
                    mime="text/calendar",
                )

            for r in reminders:
                with st.expander(f"{r.remind_at} — {r.subject}"):
                    st.write(r.body)
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("Send now", key=f"send_{r.id}"):
                            try:
                                ok, detail = email_service.send_reminder_email(r.subject or "", r.body or "")
                                if ok:
                                    rem_repo.set_status(r.id, user.id, "sent", datetime.now().isoformat())
                                    st.success("Email sent")
                                else:
                                    rem_repo.set_status(r.id, user.id, "failed")
                                    st.error(f"Failed: {detail}")
                                st.rerun()
                            except Exception as exc:
                                import logging
                                logging.exception("Send reminder failed for reminder %s", r.id)
                                st.error(f"Send failed: {exc}")
                    with col2:
                        if st.button("Cancel", key=f"can_{r.id}", type="secondary"):
                            rem_repo.set_status(r.id, user.id, "cancelled")
                            st.rerun()
                    with col3:
                        # Per-event .ics export
                        ev = ev_repo.get_by_id(r.event_id, user.id)
                        if ev:
                            ics_data = ics_service.build_ics_from_events_and_reminders(
                                [ev], [r], user.email
                            )
                            st.download_button(
                                label="📅 Download this event (.ics)",
                                data=ics_data,
                                file_name=f"memorynest_event_{ev.id}.ics",
                                mime="text/calendar",
                            )

            # Check due reminders button
            st.divider()
            if st.button("Check & send due reminders", type="primary"):
                now = datetime.now().isoformat()
                due = rem_repo.due_scheduled(user.id, now)
                if not due:
                    st.info("No due reminders")
                else:
                    for r in due:
                        try:
                            ok, detail = email_service.send_reminder_email(r.subject or "", r.body or "")
                            if ok:
                                rem_repo.set_status(r.id, user.id, "sent", datetime.now().isoformat())
                                st.success(f"Sent: {r.subject}")
                            else:
                                rem_repo.set_status(r.id, user.id, "failed")
                                st.error(f"Failed {r.subject}: {detail}")
                        except Exception as exc:
                            import logging
                            logging.exception("Bulk send failed for reminder %s", r.id)
                            st.error(f"Send failed for {r.subject}: {exc}")