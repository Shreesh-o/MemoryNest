"""History page — past conversations, reload, search."""

from __future__ import annotations

import streamlit as st

from app.services import chat_service


def render() -> None:
    user = st.session_state.user
    st.header("📜 Conversation History")

    # Sidebar search
    search_q = st.text_input("Search messages", placeholder="Keyword...")
    if search_q:
        # Use MessageRepository directly for search
        from app.database.repositories import MessageRepository
        msg_repo = MessageRepository()
        msgs = msg_repo.search(user.id, search_q, limit=50)
        if msgs:
            st.subheader(f"Search results for '{search_q}'")
            for m in msgs:
                with st.expander(f"{m.role}: {m.content[:80]}..."):
                    st.markdown(m.content)
                    if m.sources:
                        st.caption(f"Sources: {m.sources}")
        else:
            st.info("No matches")
        return

    # Conversation list using chat_service
    convos = chat_service.list_conversations(user.id)
    if not convos:
        st.info("No conversations yet. Start chatting on the Ask page!")
        return

    for c in convos:
        with st.expander(f"💬 {c.title or 'Untitled'} — {c.updated_at[:16]}"):
            # Load messages for this conversation
            convo_with_msgs = chat_service.get_conversation_with_messages(user.id, c.id)
            if convo_with_msgs:
                _, messages = convo_with_msgs
                for m in messages:
                    with st.chat_message(m.role):
                        st.markdown(m.content)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Load", key=f"load_{c.id}"):
                    st.session_state["load_convo_id"] = c.id
                    st.switch_page("app/pages/chat.py")
            with col2:
                if st.button("Delete", key=f"del_{c.id}", type="secondary"):
                    chat_service.delete_conversation(user.id, c.id)
                    st.rerun()