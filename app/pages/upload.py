"""Upload page — file picker, validation, extraction pipeline trigger."""

from __future__ import annotations

import streamlit as st

from app.services.ingest_service import (
    IngestResult,
    ingest_upload,
    process_document as _process_document,
    cleanup_failed_document as _cleanup_failed_document,
    _save_uploaded_file,
)
from app.utils.validators import sanitize_filename

__all__ = [
    "render",
    "IngestResult",
    "ingest_upload",
    "_process_document",
    "_cleanup_failed_document",
    "_save_uploaded_file",
    "sanitize_filename",
]


def render() -> None:
    user = st.session_state.user
    st.header("📤 Upload Documents")

    uploaded_files = st.file_uploader(
        "Choose files",
        type=["pdf", "docx", "txt", "png", "jpg", "jpeg", "tiff", "tif", "bmp"],
        accept_multiple_files=True,
    )

    if uploaded_files:
        for uploaded in uploaded_files:
            original_name = uploaded.name
            file_bytes = uploaded.getbuffer()

            result: IngestResult = ingest_upload(user.id, original_name, file_bytes)

            if result.status == "ready":
                st.success(f"✅ {original_name} processed ({result.chunk_count} chunks)")
            elif result.status == "duplicate":
                st.warning(f"{original_name}: {result.message}")
            elif result.status == "rejected":
                st.error(f"{original_name}: {result.message}")
            elif result.status == "error":
                st.error(f"❌ {original_name}: {result.message}")

        st.rerun()

    from app.utils.config import UPLOAD_DIR, MAX_FILE_SIZE_BYTES
    st.divider()
    st.caption(f"Upload folder: {UPLOAD_DIR}")
    st.caption(f"Max file size: {MAX_FILE_SIZE_BYTES / (1024*1024):.0f} MB")
    st.caption("Supported: PDF, DOCX, TXT, PNG, JPG, TIFF, BMP")