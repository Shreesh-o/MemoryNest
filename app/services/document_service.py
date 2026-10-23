"""Document service: list, get, delete, and retry document operations.

No Streamlit imports. Pure business logic for document management.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from app.database.repositories import ChunkRepository, DocumentRepository
from app.database.models import Document
from app.services import vector_service
from app.services.ingest_service import process_document
from app.services.link_service import rebuild_links

logger = logging.getLogger(__name__)


def list_documents(user_id: int) -> List[Document]:
    """List all documents for a user, ordered by creation date (newest first)."""
    doc_repo = DocumentRepository()
    return doc_repo.list_for_user(user_id)


def get_document(user_id: int, doc_id: int) -> Optional[Document]:
    """Get a specific document by ID for a user."""
    doc_repo = DocumentRepository()
    return doc_repo.get_by_id(doc_id, user_id)


def delete_document(user_id: int, doc_id: int) -> None:
    """Delete a document and all associated data.

    Calls DocumentRepository.delete which handles:
    - ChromaDB vector deletion (first, with retry)
    - Chunk rows deletion
    - Document row deletion
    - Stored file deletion

    Raises RuntimeError if vector cleanup fails (propagated from repository).
    """
    doc_repo = DocumentRepository()
    doc_repo.delete(doc_id, user_id)

    # Rebuild document links (non-blocking, best effort)
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