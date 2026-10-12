"""Upload page — file picker, validation, extraction pipeline trigger."""

from __future__ import annotations

import hashlib
import logging
import uuid
from pathlib import Path
import importlib

import streamlit as st

from app.database.repositories import DocumentRepository, ChunkRepository, EventRepository
from app.services import (
    extraction_service,
    ocr_service,
    chunking_service,
    embedding_service,
    vector_service,
    event_service,
)
from app.utils.validators import (
    validate_filename,
    sanitize_filename,
    validate_file_content,
    validate_size,
    file_type_for,
)

logger = logging.getLogger(__name__)


def _get_config():
    """Get the current config module (handles reloads)."""
    return importlib.reload(importlib.import_module("app.utils.config"))


def _get_upload_dir() -> Path:
    return _get_config().UPLOAD_DIR


def _get_chunk_size() -> int:
    return _get_config().CHUNK_SIZE


def _get_chunk_overlap() -> int:
    return _get_config().CHUNK_OVERLAP


def _get_max_file_size_bytes() -> int:
    return _get_config().MAX_FILE_SIZE_BYTES


def _save_uploaded_file(uploaded_file, user_id: int, original_filename: str) -> tuple[str, int]:
    """Save uploaded file to disk under user_id folder, return (stored_path, size)."""
    user_dir = _get_upload_dir() / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)

    # Sanitize and keep original extension
    safe_name = sanitize_filename(original_filename)
    ext = Path(safe_name).suffix
    unique_name = f"{uuid.uuid4().hex[:12]}{ext}"
    stored_path = user_dir / unique_name

    data = uploaded_file.getbuffer()
    stored_path.write_bytes(data)
    return str(stored_path), len(data)


def _cleanup_failed_document(doc_id: int, user_id: int, stored_path: str, reason: str) -> None:
    """Clean up partial data from a failed document and mark it as 'error'.

    Removes the partial chunk rows, their Chroma vectors, any partially
    created events, and the stored file. The document row is kept and set
    to status='error' with a readable reason, so no row is ever left stuck
    at 'uploaded'/'extracting'.
    """
    doc_repo = DocumentRepository()
    chunk_repo = ChunkRepository()
    ev_repo = EventRepository()
    vs = vector_service.get_vector_service()

    chroma_ids = chunk_repo.delete_for_document(doc_id, user_id)
    if chroma_ids:
        # Retry once on failure; if both attempts fail, verify and log error
        for attempt in range(2):
            try:
                vs.collection.delete(ids=chroma_ids)
                break
            except Exception:
                if attempt == 0:
                    continue  # retry
                # Both attempts failed: verify remaining vectors and log error
                try:
                    res = vs.collection.get(
                        where={"document_id": doc_id},
                        include=[]
                    )
                    remaining_ids = set(res.get("ids", []))
                except Exception:
                    remaining_ids = set()
                if remaining_ids:
                    logger.error(
                        "Chroma vector cleanup incomplete for doc %s; run scripts/repair.py --fix",
                        doc_id,
                        exc_info=True
                    )
                else:
                    logger.info("All Chroma vectors cleaned for doc %s (some may have been absent)", doc_id)
                # Mark document with incomplete cleanup reason
                try:
                    doc_repo = DocumentRepository()
                    cleanup_reason = f"{reason}; vector cleanup incomplete; run scripts/repair.py --fix"
                    doc_repo.update_status(doc_id, user_id, "error", cleanup_reason)
                except Exception:
                    logger.exception("Could not update doc status with vector cleanup reason")
        # End vector cleanup retry block

    ev_repo.delete_for_document(doc_id, user_id)

    path = Path(stored_path)
    if path.exists():
        path.unlink(missing_ok=True)
        try:
            path.parent.rmdir()
        except OSError:
            pass  # Directory not empty or doesn't exist

    try:
        doc_repo.update_status(doc_id, user_id, "error", reason)
    except Exception:
        logger.exception("Could not mark document %s as error", doc_id)


def _process_document(doc_id: int, user_id: int, stored_path: str, file_type: str, filename: str) -> None:
    """Extract text, chunk, embed, store in vector DB, extract events.

    On any failure the partial data is cleaned up, the document row is
    marked 'error' with a readable reason, and the original exception is
    re-raised so the UI reports the failure instead of a success.
    """
    doc_repo = DocumentRepository()
    chunk_repo = ChunkRepository()
    vs = vector_service.get_vector_service()

    try:
        doc_repo.update_status(doc_id, user_id, "extracting")
        text = extraction_service.extract_text(stored_path, file_type)
        logger.debug("doc %s: extracted %d chars of text", doc_id, len(text))

        chunks = chunking_service.chunk_text(text, max_tokens=_get_chunk_size(), overlap_tokens=_get_chunk_overlap())
        logger.debug("doc %s: %d chunks", doc_id, len(chunks))

        embeddings = embedding_service.embed_texts([c.text for c in chunks])

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
            chunk_repo.create(doc_id, user_id, chunk.index, chunk.text, chunk.token_count, chroma_id)

        vs.add_chunks(user_id, doc_id, filename, vector_chunks)

        events = event_service.extract_events(text)
        ev_repo = EventRepository()
        for e in events:
            ev_repo.create(
                user_id=user_id,
                event_text=e["event_text"],
                document_id=doc_id,
                event_date=e.get("event_date"),
                raw_date=e.get("raw_date"),
            )

        preview = text[:500]
        doc_repo.set_text(doc_id, user_id, preview, len(chunks))
        logger.debug("doc %s: ready with %d chunks", doc_id, len(chunks))

    except Exception as e:
        reason = f"{type(e).__name__}: {e}"
        logger.exception("Document processing failed for %s (doc %s): %s", filename, doc_id, reason)
        _cleanup_failed_document(doc_id, user_id, stored_path, reason)
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
            original_name = uploaded.name
            safe_name = sanitize_filename(original_name)

            # 1. Validate extension
            ok, reason = validate_filename(safe_name)
            if not ok:
                st.error(f"{original_name}: {reason}")
                continue

            # 2. Read file bytes for content validation
            file_bytes = uploaded.getbuffer()

            # 2. Validate size
            ok, reason = validate_size(len(file_bytes), _get_max_file_size_bytes())
            if not ok:
                st.error(f"{original_name}: {reason}")
                continue

            # 3. Validate content via magic bytes
            ok, reason, detected_type = validate_file_content(file_bytes, original_name)
            if not ok:
                st.error(f"{original_name}: {reason}")
                continue

            file_type = detected_type

            # 4. Compute SHA-256 hash for duplicate detection
            file_hash = hashlib.sha256(file_bytes).hexdigest()

            # 5. Check for duplicate (same user, same file hash)
            doc_repo = DocumentRepository()
            existing = doc_repo.get_by_hash(user.id, file_hash)
            if existing:
                st.warning(f"{original_name}: Already exists (uploaded as '{existing.filename}' on {existing.created_at[:10]})")
                continue

            # 6. Save file
            stored_path, size = _save_uploaded_file(uploaded, user.id, safe_name)

            # 7. Create document record with hash
            doc = doc_repo.create(user.id, original_name, stored_path, file_type, size, file_hash=file_hash)

            # 8. Process synchronously (for MVP; could be async later).
            #    _process_document re-raises after marking the row 'error'
            #    and cleaning up, so failures land in st.error below.
            with st.spinner(f"Processing {original_name}..."):
                try:
                    _process_document(doc.id, user.id, stored_path, file_type, original_name)
                except Exception as e:
                    st.error(f"❌ {original_name}: processing failed — {e}")
                    continue
                processed = doc_repo.get_by_id(doc.id, user.id)
                chunk_count = processed.chunk_count if processed else 0
                st.success(f"✅ {original_name} processed ({chunk_count} chunks)")

        st.rerun()

    st.divider()
    st.caption(f"Upload folder: {_get_upload_dir()}")
    st.caption(f"Max file size: {_get_max_file_size_bytes() / (1024*1024):.0f} MB")
    st.caption("Supported: PDF, DOCX, TXT, PNG, JPG, TIFF, BMP")