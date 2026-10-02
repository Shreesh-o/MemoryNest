"""Upload page — file picker, validation, extraction pipeline trigger."""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
import importlib

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
from app.utils.validators import (
    validate_filename,
    sanitize_filename,
    validate_file_content,
    validate_size,
    file_type_for,
)


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


def _cleanup_failed_document(doc_id: int, user_id: int, stored_path: str) -> None:
    """Clean up partial data (chunks, vectors, file) when document processing fails.
    Keeps the document row but marks it as error."""
    from app.database.repositories import DocumentRepository, ChunkRepository
    from app.services import vector_service
    from pathlib import Path

    doc_repo = DocumentRepository()
    chunk_repo = ChunkRepository()
    vs = vector_service.get_vector_service()

    # Delete chunks and get chroma_ids
    chroma_ids = chunk_repo.delete_for_document(doc_id, user_id)

    # Delete vectors from ChromaDB
    if chroma_ids:
        vs.collection.delete(ids=chroma_ids)

    # Delete stored file
    path = Path(stored_path)
    if path.exists():
        path.unlink(missing_ok=True)
        # Try to remove empty user directory
        try:
            path.parent.rmdir()
        except OSError:
            pass  # Directory not empty or doesn't exist


def _process_document(doc_id: int, user_id: int, stored_path: str, file_type: str, filename: str) -> None:
    """Extract text, chunk, embed, store in vector DB, extract events."""
    import sys
    print(f"DEBUG _process_document ENTRY: doc_id={doc_id}, user_id={user_id}, file_type={file_type}", flush=True)
    sys.stdout.flush()
    print("DEBUG _process_document: after imports", flush=True)
    sys.stdout.flush()
    from app.database.repositories import DocumentRepository, ChunkRepository
    from app.services import vector_service
    from app.database.repositories import EventRepository

    doc_repo = DocumentRepository()
    chunk_repo = ChunkRepository()
    vs = vector_service.get_vector_service()

    try:
        doc_repo.update_status(doc_id, user_id, "extracting")
        text = extraction_service.extract_text(stored_path, file_type)
        print(f"DEBUG _process_document: extracted text length = {len(text)}", flush=True)

        # Chunk
        chunks = chunking_service.chunk_text(text, max_tokens=_get_chunk_size(), overlap_tokens=_get_chunk_overlap())
        print(f"DEBUG: chunks count = {len(chunks)}", flush=True)

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
        print(f"DEBUG _process_document: calling set_text with preview={repr(preview)}, chunks={len(chunks)}", flush=True)
        import sys
        sys.stdout.flush()
        doc_repo.set_text(doc_id, user_id, preview, len(chunks))
        print(f"DEBUG _process_document: set_text returned", flush=True)
        sys.stdout.flush()

    except Exception as e:
        # Clean up partial data (chunks, vectors, file)
        from app.database.repositories import DocumentRepository, ChunkRepository
        from app.services import vector_service
        from app.utils.config import UPLOAD_DIR
        from pathlib import Path

        doc_repo = DocumentRepository()
        chunk_repo = ChunkRepository()
        vs = vector_service.get_vector_service()

        # Delete chunks and get chroma_ids
        chroma_ids = chunk_repo.delete_for_document(doc_id, user_id)

        # Delete vectors from ChromaDB
        if chroma_ids:
            vs.collection.delete(ids=chroma_ids)

        # Delete stored file
        path = Path(stored_path)
        if path.exists():
            path.unlink(missing_ok=True)
            # Try to remove empty user directory
            try:
                path.parent.rmdir()
            except OSError:
                pass  # Directory not empty or doesn't exist


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
            ok, reason, detected_type = validate_file_content(file_bytes)
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

            # 8. Process synchronously (for MVP; could be async later)
            with st.spinner(f"Processing {original_name}..."):
                try:
                    _process_document(doc.id, user.id, stored_path, file_type, original_name)
                    st.success(f"✅ {original_name} processed ({doc.chunk_count} chunks)")
                except Exception as e:
                    import logging
                    logging.exception("Upload processing failed for %s", original_name)
                    st.error(f"❌ {original_name}: {e}")

        st.rerun()

    st.divider()
    st.caption(f"Upload folder: {_get_upload_dir()}")
    st.caption(f"Max file size: {_get_max_file_size_bytes() / (1024*1024):.0f} MB")
    st.caption("Supported: PDF, DOCX, TXT, PNG, JPG, TIFF, BMP")