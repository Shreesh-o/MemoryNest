"""Documents page — browse, preview, delete stored documents."""

from __future__ import annotations

import streamlit as st

from app.database.repositories import DocumentRepository, ChunkRepository
from app.services import vector_service


def render() -> None:
    user = st.session_state.user
    st.header("📁 Your Documents")

    doc_repo = DocumentRepository()
    chunk_repo = ChunkRepository()
    vs = vector_service.get_vector_service()

    docs = doc_repo.list_for_user(user.id)
    if not docs:
        st.info("No documents yet. Go to Upload to add some!")
        return

    for d in docs:
        status_icon = {"ready": "✅", "uploaded": "⏳", "extracting": "⚙️", "error": "❌"}.get(d.status, "❓")
        with st.expander(f"{status_icon} {d.filename} — {d.file_type} — {d.size_bytes/1024:.1f} KB — {d.created_at[:16]}"):
            if d.error_message:
                st.error(d.error_message)
            if d.text_preview:
                st.text_area("Preview", d.text_preview, height=100, disabled=True)
            st.caption(f"Chunks: {d.chunk_count} | ID: {d.id}")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Delete", key=f"del_doc_{d.id}", type="secondary"):
                    # Delete chunks from vector DB
                    chroma_ids = chunk_repo.delete_for_document(d.id, user.id)
                    if chroma_ids:
                        vs.delete_document(d.id, user.id)
                    # Delete from SQL
                    doc_repo.delete(d.id, user.id)
                    st.success("Document deleted")
                    st.rerun()
            with col2:
                if d.status == "error" and st.button("Retry extraction", key=f"retry_{d.id}"):
                    st.info("Retry not yet implemented")