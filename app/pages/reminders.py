"""Reminders page — extracted dates/events, confirmation, email reminders, .ics export."""

from __future__ import annotations

import streamlit as st
from datetime import datetime

from app.database.repositories import DocumentRepository, EventRepository, ReminderRepository
from app.services import email_service, ics_service, reminder_flow_service


def _get_confirmed_events_with_reminders(ev_repo, rem_repo, user_id):
    """Get confirmed events with their reminders for .ics export."""
    events = ev_repo.list_for_user(user_id, status="confirmed")
    if not events:
        return [], []
    reminders = rem_repo.list_for_user(user_id, status="scheduled")
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
                    try:
                        events = reminder_flow_service.extract_events_for_document(user.id, doc.id)
                        if not events:
                            st.info("No events found")
                        else:
                            st.success(f"Extracted {len(events)} event(s)")
                            st.rerun()
                    except ValueError as e:
                        st.error(str(e))
                    except RuntimeError as e:
                        import logging
                        logging.exception("Event extraction failed for doc %s", doc.id)
                        st.error(str(e))

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
                                reminder_flow_service.confirm_event(user.id, e.id)
                                st.success("Confirmed and reminder scheduled")
                                st.rerun()
                            except ValueError as e:
                                st.error(str(e))
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
                            reminder_flow_service.discard_event(user.id, e.id)
                            st.rerun()

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

            st.divider()
            if st.button("Check & send due reminders", type="primary"):
                try:
                    result = reminder_flow_service.check_and_send_due(user.id)
                    if not result.configured:
                        st.info(
                            result.errors[0]
                            if result.errors
                            else "Email is not set up. Add EMAIL_USERNAME and EMAIL_APP_PASSWORD to the .env file."
                        )
                    elif result.sent == 0 and result.failed == 0:
                        st.info("No due reminders")
                    else:
                        if result.sent:
                            st.success(f"Sent {result.sent} reminder(s)")
                        if result.failed:
                            st.error(f"Failed {result.failed} reminder(s)")
                            for err in result.errors:
                                st.caption(err)
                except Exception as exc:
                    import logging
                    logging.exception("Check due reminders failed for user %s", user.id)
                    st.error(f"Check failed: {exc}")