"""Ingest service: file validation, storage, and document processing.

No Streamlit imports. Pure business logic for uploading and processing documents.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Union

import importlib

from app.database.repositories import DocumentRepository, ChunkRepository, EventRepository
from app.services import (
    extraction_service,
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
)

logger = logging.getLogger(__name__)


@dataclass
class IngestResult:
    status: str  # "ready" | "duplicate" | "rejected" | "error"
    message: str
    doc_id: int | None
    chunk_count: int


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


def _save_file_to_disk(user_id: int, original_filename: str, file_bytes: bytes) -> tuple[str, int]:
    """Save file bytes to disk under user_id folder, return (stored_path, size)."""
    user_dir = _get_upload_dir() / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)

    safe_name = sanitize_filename(original_filename)
    ext = Path(safe_name).suffix
    unique_name = f"{uuid.uuid4().hex[:12]}{ext}"
    stored_path = user_dir / unique_name

    stored_path.write_bytes(file_bytes)
    return str(stored_path), len(file_bytes)


def _save_uploaded_file(uploaded_file, user_id: int, original_filename: str) -> tuple[str, int]:
    """Backward-compatible wrapper for tests: takes a Streamlit-like uploaded file object."""
    file_bytes = uploaded_file.getbuffer()
    return _save_file_to_disk(user_id, original_filename, file_bytes)


def cleanup_failed_document(doc_id: int, user_id: int, stored_path: str, reason: str) -> None:
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


def process_document(doc_id: int, user_id: int, stored_path: str, file_type: str, filename: str) -> None:
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
        chunk_dicts = []
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
            chunk_dicts.append(
                {
                    "document_id": doc_id,
                    "user_id": user_id,
                    "chunk_index": chunk.index,
                    "content": chunk.text,
                    "token_count": chunk.token_count,
                    "chroma_id": chroma_id,
                }
            )

        if chunk_dicts:
            chunk_repo.create_batch(chunk_dicts)

        vs.add_chunks(user_id, doc_id, filename, vector_chunks)

        events = event_service.extract_events(text)
        if events:
            ev_repo = EventRepository()
            ev_data = [
                {
                    "user_id": user_id,
                    "document_id": doc_id,
                    "event_text": e["event_text"],
                    "event_date": e.get("event_date"),
                    "raw_date": e.get("raw_date"),
                }
                for e in events
            ]
            ev_repo.create_batch(ev_data)

        preview = text[:500]
        doc_repo.set_text(doc_id, user_id, preview, len(chunks))
        logger.debug("doc %s: ready with %d chunks", doc_id, len(chunks))

    except Exception as e:
        reason = f"{type(e).__name__}: {e}"
        logger.exception("Document processing failed for %s (doc %s): %s", filename, doc_id, reason)
        cleanup_failed_document(doc_id, user_id, stored_path, reason)
        raise


def ingest_upload(user_id: int, original_name: str, file_bytes: Union[bytes, bytearray, memoryview]) -> IngestResult:
    """Full upload flow: validate, dedupe, save, create record, process.

    Returns an IngestResult with status and details. Never raises; all
    failures return status="error" with a real reason and are logged.
    """
    # Ensure bytes type
    if isinstance(file_bytes, (bytearray, memoryview)):
        file_bytes = bytes(file_bytes)

    # 1. Validate extension
    safe_name = sanitize_filename(original_name)
    ok, reason = validate_filename(safe_name)
    if not ok:
        return IngestResult(status="rejected", message=reason, doc_id=None, chunk_count=0)

    # 2. Validate size
    ok, reason = validate_size(len(file_bytes), _get_max_file_size_bytes())
    if not ok:
        return IngestResult(status="rejected", message=reason, doc_id=None, chunk_count=0)

    # 3. Validate content via magic bytes (pass original filename for .txt handling)
    ok, reason, detected_type = validate_file_content(file_bytes, original_name)
    if not ok:
        return IngestResult(status="rejected", message=reason, doc_id=None, chunk_count=0)

    file_type = detected_type

    # 4. Compute SHA-256 hash for duplicate detection
    file_hash = hashlib.sha256(file_bytes).hexdigest()

    # 5. Check for duplicate (same user, same file hash)
    doc_repo = DocumentRepository()
    existing = doc_repo.get_by_hash(user_id, file_hash)
    if existing:
        return IngestResult(
            status="duplicate",
            message=f"Already exists (uploaded as '{existing.filename}' on {existing.created_at[:10]})",
            doc_id=existing.id,
            chunk_count=existing.chunk_count or 0,
        )

    # 6. Save file
    stored_path, size = _save_file_to_disk(user_id, safe_name, file_bytes)

    # 7. Create document record with hash
    doc = doc_repo.create(user_id, original_name, stored_path, file_type, size, file_hash=file_hash)

    # 8. Process synchronously
    try:
        process_document(doc.id, user_id, stored_path, file_type, original_name)
    except Exception as e:
        return IngestResult(
            status="error",
            message=f"processing failed — {e}",
            doc_id=doc.id,
            chunk_count=0,
        )

    processed = doc_repo.get_by_id(doc.id, user_id)
    chunk_count = processed.chunk_count if processed else 0
    return IngestResult(
        status="ready",
        message=f"processed ({chunk_count} chunks)",
        doc_id=doc.id,
        chunk_count=chunk_count,
    )