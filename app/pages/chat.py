"""Chat page — natural-language questions answered via local RAG."""

from __future__ import annotations

import streamlit as st

from app.services import rag_service


def render() -> None:
    user = st.session_state.user
    st.header("💬 Ask your documents")

    # Initialize conversation state
    if "rag_messages" not in st.session_state:
        st.session_state.rag_messages = []

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
                result = rag_service.rag_answer(user.id, prompt)
            st.markdown(result.answer)
            if result.sources:
                with st.expander("Sources"):
                    for s in result.sources:
                        st.caption(
                            f"📄 {s['document']} · chunk {s['chunk_index']} · "
                            f"similarity {s['similarity']:.3f}"
                        )

        # Add assistant message
        st.session_state.rag_messages.append(
            {"role": "assistant", "content": result.answer, "sources": result.sources}
        )

    # Clear button
    if st.session_state.rag_messages:
        if st.button("Clear conversation"):
            st.session_state.rag_messages = []
            st.rerun()