"""Summaries page — generate and review document summaries (+ TTS)."""

from __future__ import annotations

import os

import streamlit as st

from app.database.repositories import DocumentRepository, SummaryRepository
from app.services import summary_flow_service, summary_service, tts_service


def render() -> None:
    user = st.session_state.user
    st.header("\U0001F4DD Document Summaries")

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
                if st.button("\U0001F50A Play", key=f"tts_{s.id}"):
                    if tts_service.tts_available():
                        with st.spinner("Generating audio..."):
                            try:
                                path = tts_service.synthesize_to_file(s.summary_text)
                                if path and os.path.exists(path) and os.path.getsize(path) > 0:
                                    st.audio(path)
                                    with open(path, "rb") as f:
                                        st.download_button(
                                            label="Download WAV",
                                            data=f,
                                            file_name=os.path.basename(path),
                                            mime="audio/wav",
                                            key=f"dl_{s.id}",
                                        )
                                else:
                                    st.error("Audio file was not created")
                            except RuntimeError as e:
                                st.error(str(e))
                    else:
                        st.warning("TTS unavailable (install espeak-ng: pacman -S espeak-ng)")

    # Generate new summary
    st.divider()
    if st.button("Generate new summary", type="primary"):
        with st.spinner("Generating summary... (may take a minute)"):
            try:
                s = summary_flow_service.get_or_create_summary(user.id, doc.id, force=True)
                st.success("Summary generated!")
                st.rerun()
            except Exception as e:
                import logging
                logging.exception("Summary generation failed for doc %s", doc.id)
                st.error(f"Summary generation failed: {e}")
