"""Documents page — browse, preview, delete stored documents."""

from __future__ import annotations

import streamlit as st

from app.services.document_service import delete_document, list_documents, retry_extraction


def render() -> None:
    user = st.session_state.user
    st.header("📁 Your Documents")

    docs = list_documents(user.id)
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
                    try:
                        delete_document(user.id, d.id)
                    except RuntimeError:
                        st.error(
                            "Document was NOT deleted: vector cleanup failed. "
                            "Nothing was removed. Try again, or run "
                            "scripts/repair.py --fix"
                        )
                    else:
                        st.rerun()
            with col2:
                if d.status == "error" and st.button("Retry extraction", key=f"retry_{d.id}"):
                    try:
                        retry_extraction(user.id, d.id)
                    except Exception as e:
                        st.error(f"Retry failed: {e}")
                    else:
                        st.rerun()