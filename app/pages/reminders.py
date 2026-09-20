"""Reminders page — extracted dates/events, confirmation, email reminders."""

from __future__ import annotations

import streamlit as st
from datetime import datetime

from app.database.repositories import DocumentRepository, EventRepository, ReminderRepository
from app.services import event_service, email_service
from app.utils.config import RAG_MIN_SIMILARITY


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
                    # Use text_preview for now; in production, fetch full text from chunks
                    text = doc.text_preview or ""
                    if not text:
                        st.warning("Document has no text preview")
                    else:
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
                            ev_repo.set_status(e.id, user.id, "confirmed")
                            # Create reminder for 1 day before event date (or same day if no date)
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
                    with col2:
                        if st.button("Skip", key=f"skip_{e.id}"):
                            ev_repo.set_status(e.id, user.id, "skipped")
                            st.rerun()
                    with col3:
                        if st.button("Delete", key=f"del_ev_{e.id}", type="secondary"):
                            ev_repo.delete(e.id, user.id)
                            st.rerun()

    with tab_scheduled:
        st.subheader("Scheduled reminders")
        reminders = rem_repo.list_for_user(user.id, status="scheduled")
        if not reminders:
            st.info("No scheduled reminders")
        else:
            for r in reminders:
                with st.expander(f"{r.remind_at} — {r.subject}"):
                    st.write(r.body)
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Send now", key=f"send_{r.id}"):
                            ok, detail = email_service.send_reminder_email(r.subject or "", r.body or "")
                            if ok:
                                rem_repo.set_status(r.id, user.id, "sent", datetime.now().isoformat())
                                st.success("Email sent")
                            else:
                                rem_repo.set_status(r.id, user.id, "failed")
                                st.error(f"Failed: {detail}")
                            st.rerun()
                    with col2:
                        if st.button("Cancel", key=f"can_{r.id}", type="secondary"):
                            rem_repo.set_status(r.id, user.id, "cancelled")
                            st.rerun()

            # Check due reminders button
            st.divider()
            if st.button("Check & send due reminders", type="primary"):
                now = datetime.now().isoformat()
                due = rem_repo.due_scheduled(user.id, now)
                if not due:
                    st.info("No due reminders")
                else:
                    for r in due:
                        ok, detail = email_service.send_reminder_email(r.subject or "", r.body or "")
                        if ok:
                            rem_repo.set_status(r.id, user.id, "sent", datetime.now().isoformat())
                            st.success(f"Sent: {r.subject}")
                        else:
                            rem_repo.set_status(r.id, user.id, "failed")
                            st.error(f"Failed {r.subject}: {detail}")