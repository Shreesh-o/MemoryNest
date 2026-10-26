"""Document service: list, get, delete, and retry document operations.

No Streamlit imports. Pure business logic for document management.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from app.database.repositories import ChunkRepository, DocumentRepository
from app.database.models import Document
from app.services import vector_service
from app.services.chunking_service import reconstruct_text_from_chunks
from app.services.ingest_service import process_document
from app.services.link_service import rebuild_links
from app.services.text_cache_service import get_cached_text

logger = logging.getLogger(__name__)


def list_documents(user_id: int) -> List[Document]:
    """List all documents for a user, ordered by creation date (newest first)."""
    doc_repo = DocumentRepository()
    return doc_repo.list_for_user(user_id)


def get_document(user_id: int, doc_id: int) -> Optional[Document]:
    """Get a specific document by ID for a user."""
    doc_repo = DocumentRepository()
    return doc_repo.get_by_id(doc_id, user_id)


def get_document_full_text(user_id: int, doc_id: int, doc: Optional[Document] = None) -> str:
    """Retrieve the complete text of a document for summarization, reminder extraction, etc.

    Hierarchical retrieval strategy:
    1. Prefer text_cache_service.get_cached_text (canonical extraction from stored file
       with normalization and disk caching).
    2. Fallback to reconstructing text from ordered database chunks scoped to user_id
       and doc_id via chunking_service.reconstruct_text_from_chunks, deduplicating boundary overlap.
    3. If neither stored file nor chunks are available:
       - If the document is known to be truncated (chunk_count > 1, or chunk_count == 1
         and text_preview is at or above the 500-char preview cap), raise RuntimeError
         (never silently treat a truncated preview as full text).
       - If chunk_count <= 1 and text_preview represents the entire document (< 500 chars),
         return text_preview.
    4. Explicitly handles missing files, missing chunks, extraction failures, and empty documents.

    Args:
        user_id: The ID of the document owner.
        doc_id: The ID of the document.
        doc: Optional pre-fetched Document model. If None, fetched from repository.

    Returns:
        The full text of the document.

    Raises:
        ValueError: If document not found, document is not ready, or document has no text content.
        RuntimeError: If document text cannot be recovered (e.g. file missing and chunks missing for truncated doc).
    """
    doc_repo = DocumentRepository()
    if doc is None or doc.user_id != user_id or doc.id != doc_id:
        doc = doc_repo.get_by_id(doc_id, user_id)

    if not doc:
        raise ValueError("Document not found")

    if doc.status != "ready":
        raise ValueError(f"Document is not ready (status: {doc.status})")

    # 1. Try text_cache_service (canonical extraction from stored file)
    text: Optional[str] = None
    if doc.stored_path:
        try:
            cached_text, _ = get_cached_text(doc.id, doc.stored_path, doc.file_type)
            if cached_text and cached_text.strip():
                text = cached_text
        except Exception as e:
            logger.warning(
                "Unable to retrieve cached/extracted text for doc %s from file %s: %s",
                doc_id, doc.stored_path, e,
            )

    # 2. Fallback: reconstruct from database chunks scoped to user and document
    if not text:
        chunk_repo = ChunkRepository()
        chunks = chunk_repo.list_for_document(doc.id, user_id)
        if chunks:
            reconstructed = reconstruct_text_from_chunks(chunks)
            if reconstructed and reconstructed.strip():
                text = reconstructed

    # 3. Handle unrecoverable documents or fallback to preview only if complete
    if not text:
        preview = (doc.text_preview or "").strip()
        is_known_truncated = (doc.chunk_count > 1) or (
            doc.chunk_count == 1 and len(preview) >= 500
        )
        if is_known_truncated:
            raise RuntimeError(
                f"Document {doc_id} text cannot be recovered: original file and chunks are unavailable"
            )
        if preview:
            text = preview

    # 4. Empty document check
    if not text or not text.strip():
        raise ValueError("Document has no text content")

    return text


def delete_document(user_id: int, doc_id: int) -> None:
    """Coordinate document deletion across vector store, text cache, database, and disk.

    1. Deletes ChromaDB vectors first (with retry). If this fails, RuntimeError propagates
       before touching SQLite rows or stored files, preserving state for repair.
    2. Invalidates extracted text and HTML cache.
    3. Deletes document chunks and document row from SQLite.
    4. Deletes stored file from disk and cleans up empty directory.
    5. Rebuilds document links for the user (best effort).
    """
    from pathlib import Path
    from app.services.text_cache_service import invalidate_text_cache

    doc_repo = DocumentRepository()
    chunk_repo = ChunkRepository()

    doc = doc_repo.get_by_id(doc_id, user_id)
    if not doc:
        return

    # 1. Delete Chroma vectors FIRST; if this fails, raise RuntimeError before SQLite deletion
    vs = vector_service.get_vector_service()
    vs.delete_document(doc_id, user_id)

    # 2. Invalidate text cache
    invalidate_text_cache(doc_id)

    # 3. Delete database rows
    chunk_repo.delete_for_document(doc_id, user_id)
    doc_repo.delete_row(doc_id, user_id)

    # 4. Delete stored file
    if doc.stored_path:
        path = Path(doc.stored_path)
        if path.exists():
            path.unlink(missing_ok=True)
            try:
                path.parent.rmdir()
            except OSError:
                pass

    # 5. Rebuild document links (non-blocking, best effort)
    try:
        rebuild_links(user_id)
    except Exception as e:
        logger.warning("Failed to rebuild document links for user %s after delete: %s", user_id, e)


def retry_extraction(user_id: int, doc_id: int) -> None:
    """Retry document extraction for a failed document.

    Re-processes the document from the stored file. If the document
    doesn't exist or doesn't belong to the user, raises ValueError.
    If the document status is not 'error', raises ValueError.
    """
    doc = get_document(user_id, doc_id)
    if not doc:
        raise ValueError(f"Document {doc_id} not found for user {user_id}")
    if doc.status != "error":
        raise ValueError(f"Document {doc_id} is not in error state (status: {doc.status})")

    # Clean up existing chunks and vectors before reprocessing
    chunk_repo = ChunkRepository()
    vs = vector_service.get_vector_service()
    chroma_ids = chunk_repo.delete_for_document(doc_id, user_id)
    if chroma_ids:
        try:
            vs.collection.delete(ids=chroma_ids)
        except Exception:
            logger.warning("Failed to delete Chroma vectors for doc %s during retry", doc_id)

    # Also delete any existing events
    from app.database.repositories import EventRepository
    ev_repo = EventRepository()
    ev_repo.delete_for_document(doc_id, user_id)

    # Re-process the document
    process_document(doc.id, user_id, doc.stored_path, doc.file_type, doc.filename)

    # Rebuild document links (non-blocking, best effort)
    try:
        rebuild_links(user_id)
    except Exception as e:
        logger.warning("Failed to rebuild document links for user %s after retry: %s", user_id, e)