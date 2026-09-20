"""Dashboard — counts, upcoming deadlines, recent activity."""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from app.database.repositories import (
    ConversationRepository,
    DocumentRepository,
    EventRepository,
    ReminderRepository,
    SummaryRepository,
)


def render() -> None:
    user = st.session_state.user
    st.header("📊 Dashboard")

    doc_repo = DocumentRepository()
    sum_repo = SummaryRepository()
    convo_repo = ConversationRepository()
    ev_repo = EventRepository()
    rem_repo = ReminderRepository()

    # Stats row
    docs = doc_repo.list_for_user(user.id)
    ready_docs = [d for d in docs if d.status == "ready"]
    total_chunks = sum(d.chunk_count for d in ready_docs)
    summaries = sum_repo.list_for_user(user.id)
    convos = convo_repo.list_for_user(user.id)
    pending_events = ev_repo.list_for_user(user.id, status="pending")
    confirmed_events = ev_repo.list_for_user(user.id, status="confirmed")
    due_reminders = rem_repo.due_scheduled(user.id, datetime.now().isoformat())
    scheduled_reminders = rem_repo.list_for_user(user.id, status="scheduled")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Documents", len(ready_docs), f"{len(docs) - len(ready_docs)} processing")
    col2.metric("Total chunks", total_chunks)
    col3.metric("Summaries", len(summaries))
    col4.metric("Conversations", len(convos))

    st.divider()

    # Upcoming deadlines
    st.subheader("⏰ Upcoming deadlines")
    if confirmed_events:
        for e in sorted(confirmed_events, key=lambda x: x.event_date or "9999")[:5]:
            if e.event_date:
                st.write(f"📅 **{e.event_date}** — {e.event_text[:80]}")
            else:
                st.write(f"📌 **TBD** — {e.event_text[:80]}")
    else:
        st.info("No confirmed events")

    st.divider()

    # Pending confirmations
    st.subheader("❓ Pending event confirmations")
    if pending_events:
        for e in pending_events[:5]:
            st.write(f"📄 {e.raw_date or 'No date'} — {e.event_text[:80]}")
        if st.button("Go to Reminders →"):
            st.switch_page("app/pages/reminders.py")
    else:
        st.info("No pending events")

    st.divider()

    # Due reminders
    st.subheader("📬 Due reminders")
    if due_reminders:
        for r in due_reminders[:5]:
            st.warning(f"⏰ **{r.remind_at}** — {r.subject}")
        if st.button("Send due reminders now"):
            st.switch_page("app/pages/reminders.py")
    else:
        st.info("No reminders due right now")

    st.divider()

    # Recent activity (last 5 conversations)
    st.subheader("💬 Recent conversations")
    if convos:
        for c in convos[:5]:
            st.write(f"💬 {c.title or 'Untitled'} — updated {c.updated_at[:16]}")
    else:
        st.info("No conversations yet")