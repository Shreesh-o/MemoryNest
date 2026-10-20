"""Chat page — natural-language questions answered via local RAG."""

from __future__ import annotations

import streamlit as st

from app.services import chat_service


def render() -> None:
    user = st.session_state.user
    st.header("💬 Ask your documents")

    # Initialize conversation state
    if "rag_messages" not in st.session_state:
        st.session_state.rag_messages = []
    if "current_conversation_id" not in st.session_state:
        st.session_state.current_conversation_id = None

    # Display chat history
    for msg in st.session_state.rag_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sources"):
                with st.expander("Sources"):
                    for s in msg["sources"]:
                        st.caption(
                            f"📄 {s['document']} · chunk {s['chunk_index']} · "
                            f"similarity {s['similarity']:.3f}"
                        )

    # Chat input
    if prompt := st.chat_input("Ask a question about your documents..."):
        # Add user message
        st.session_state.rag_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get RAG answer
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    result = chat_service.ask(
                        user.id,
                        prompt,
                        st.session_state.current_conversation_id,
                    )
                    st.session_state.current_conversation_id = result.conversation_id
                except RuntimeError as e:
                    import logging
                    logging.exception("RAG query failed for user %s", user.id)
                    st.error(str(e))
                    result = None
            if result:
                st.markdown(result.answer)
            if result.sources:
                with st.expander("Sources"):
                    for s in result.sources:
                        st.caption(
                            f"📄 {s['document']} · chunk {s['chunk_index']} · "
                            f"similarity {s['similarity']:.3f}"
                        )

        # Add assistant message
        if result:
            st.session_state.rag_messages.append(
                {"role": "assistant", "content": result.answer, "sources": result.sources}
            )

    # Clear / New conversation button
    if st.session_state.rag_messages:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Clear conversation"):
                st.session_state.rag_messages = []
                st.session_state.current_conversation_id = None
                st.rerun()
        with col2:
            if st.button("New chat"):
                st.session_state.rag_messages = []
                st.session_state.current_conversation_id = None
                st.rerun()