"""Summaries page — generate and review document summaries (+ TTS)."""

from __future__ import annotations

import streamlit as st

from app.database.repositories import DocumentRepository, SummaryRepository
from app.services import summary_service, tts_service


def render() -> None:
    user = st.session_state.user
    st.header("📝 Document Summaries")

    doc_repo = DocumentRepository()
    sum_repo = SummaryRepository()

    docs = doc_repo.list_for_user(user.id)
    ready_docs = [d for d in docs if d.status == "ready"]

    if not ready_docs:
        st.info("No processed documents yet. Upload some files first!")
        return

    # Select document
    doc_labels = {f"{d.filename} ({d.chunk_count} chunks)": d for d in ready_docs}
    selected_label = st.selectbox("Select document", list(doc_labels.keys()))
    doc = doc_labels[selected_label]

    # Existing summaries
    existing = sum_repo.list_for_document(doc.id, user.id)
    if existing:
        st.subheader("Saved summaries")
        for s in existing:
            with st.expander(f"Summary from {s.created_at[:16]}"):
                st.markdown(s.summary_text)
                if st.button("🔊 Play", key=f"tts_{s.id}"):
                    if tts_service.tts_available():
                        with st.spinner("Generating audio..."):
                            path = tts_service.synthesize_to_file(s.summary_text)
                            if path:
                                st.audio(path)
                            else:
                                st.error("TTS generation failed")
                    else:
                        st.warning("TTS unavailable (install espeak-ng: pacman -S espeak-ng)")

    # Generate new summary
    st.divider()
    if st.button("Generate new summary", type="primary"):
        with st.spinner("Generating summary... (may take a minute)"):
            # Get full text from chunks (we don't store full text in DB, only preview)
            # For now, use the text_preview as source - in production, we'd reconstruct from chunks
            full_text = doc.text_preview or "No text preview available"
            summary_text = summary_service.summarize_document(full_text)

        if summary_text:
            s = sum_repo.create(doc.id, user.id, summary_text)
            st.success("Summary generated!")
            st.rerun()
        else:
            st.error("Summary generation failed (check LLM availability)")