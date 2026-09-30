"""Upload page — file picker, validation, extraction pipeline trigger."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import streamlit as st

from app.database.database import init_db
from app.database.repositories import DocumentRepository, ChunkRepository
from app.services import (
    extraction_service,
    ocr_service,
    chunking_service,
    embedding_service,
    vector_service,
    event_service,
)
from app.utils.config import UPLOAD_DIR, CHUNK_SIZE, CHUNK_OVERLAP
from app.utils.validators import validate_filename, validate_size, file_type_for


def _save_uploaded_file(uploaded_file, user_id: int) -> tuple[str, int]:
    """Save uploaded file to disk, return (stored_path, size)."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(uploaded_file.name).suffix
    unique_name = f"{user_id}_{uuid.uuid4().hex[:8]}{ext}"
    stored_path = UPLOAD_DIR / unique_name
    data = uploaded_file.getbuffer()
    stored_path.write_bytes(data)
    return str(stored_path), len(data)


def _process_document(doc_id: int, user_id: int, stored_path: str, file_type: str, filename: str) -> None:
    """Extract text, chunk, embed, store in vector DB, extract events."""
    doc_repo = DocumentRepository()
    chunk_repo = ChunkRepository()
    vs = vector_service.get_vector_service()

    try:
        doc_repo.update_status(doc_id, user_id, "extracting")
        text = extraction_service.extract_text(stored_path, file_type)

        # Chunk
        chunks = chunking_service.chunk_text(text, max_tokens=CHUNK_SIZE, overlap_tokens=CHUNK_OVERLAP)

        # Embed
        chunk_texts = [c.text for c in chunks]
        embeddings = embedding_service.embed_texts(chunk_texts)

        # Prepare for vector DB
        vector_chunks = []
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            chroma_id = f"doc-{doc_id}-chunk-{i}"
            vector_chunks.append(
                {
                    "index": chunk.index,
                    "text": chunk.text,
                    "token_count": chunk.token_count,
                    "chroma_id": chroma_id,
                    "embedding": emb,
                }
            )
            # Save chunk metadata to SQL
            chunk_repo.create(doc_id, user_id, chunk.index, chunk.text, chunk.token_count, chroma_id)

        # Store in vector DB
        vs.add_chunks(user_id, doc_id, filename, vector_chunks)

        # Extract events
        events = event_service.extract_events(text)
        from app.database.repositories import EventRepository
        ev_repo = EventRepository()
        for e in events:
            ev_repo.create(
                user_id=user_id,
                event_text=e["event_text"],
                document_id=doc_id,
                event_date=e.get("event_date"),
                raw_date=e.get("raw_date"),
            )

        # Update document status
        preview = text[:500]
        doc_repo.set_text(doc_id, user_id, preview, len(chunks))

    except Exception as e:
        doc_repo.update_status(doc_id, user_id, "error", str(e))
        raise


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
            # Validate
            ok, reason = validate_filename(uploaded.name)
            if not ok:
                st.error(f"{uploaded.name}: {reason}")
                continue
            ok, reason = validate_size(uploaded.size)
            if not ok:
                st.error(f"{uploaded.name}: {reason}")
                continue

            file_type = file_type_for(uploaded.name)
            stored_path, size = _save_uploaded_file(uploaded, user.id)

            # Create document record
            doc_repo = DocumentRepository()
            doc = doc_repo.create(user.id, uploaded.name, stored_path, file_type, size)

            # Process synchronously (for MVP; could be async later)
            with st.spinner(f"Processing {uploaded.name}..."):
                try:
                    _process_document(doc.id, user.id, stored_path, file_type, uploaded.name)
                    st.success(f"✅ {uploaded.name} processed ({doc.chunk_count} chunks)")
                except Exception as e:
                    import logging
                    logging.exception("Upload processing failed for %s", uploaded.name)
                    st.error(f"❌ {uploaded.name}: {e}")

        st.rerun()

    st.divider()
    st.caption(f"Upload folder: {UPLOAD_DIR}")
    st.caption(f"Max file size: 25 MB")
    st.caption("Supported: PDF, DOCX, TXT, PNG/JPG/TIFF/BMP (OCR)")