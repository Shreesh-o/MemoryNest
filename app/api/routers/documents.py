"""Documents router: list, get, delete, upload, retry."""

from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status

from app.api.deps import get_current_user
from app.api.schemas import DocumentPublic, IngestResultResponse
from app.services.ingest_service import ingest_upload, IngestResult
from app.services.document_service import list_documents, get_document, delete_document, retry_extraction
from app.utils.config import MAX_FILE_SIZE_BYTES

logger = logging.getLogger(__name__)

router = APIRouter()


def _truncate(text: str | None, limit: int = 500) -> str | None:
    if text is None:
        return None
    return text[:limit]


def _doc_to_public(doc) -> DocumentPublic:
    return DocumentPublic(
        id=doc.id,
        filename=doc.filename,
        file_type=doc.file_type,
        status=doc.status,
        chunk_count=doc.chunk_count,
        error_message=doc.error_message,
        created_at=doc.created_at,
        text_preview=_truncate(doc.text_preview),
    )


@router.get("/api/documents", response_model=List[DocumentPublic])
def api_list_documents(user=Depends(get_current_user)):
    """List all documents for the current user."""
    docs = list_documents(user.id)
    return [_doc_to_public(d) for d in docs]


@router.get("/api/documents/{doc_id}", response_model=DocumentPublic)
def api_get_document(doc_id: int, user=Depends(get_current_user)):
    """Get a single document by ID."""
    doc = get_document(user.id, doc_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return _doc_to_public(doc)


@router.delete("/api/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def api_delete_document(doc_id: int, user=Depends(get_current_user)):
    """Delete a document and all associated data."""
    # First check if the document exists (so we can return 404, not 403)
    doc = get_document(user.id, doc_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    try:
        delete_document(user.id, doc_id)
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/api/documents/{doc_id}/retry", response_model=DocumentPublic)
def api_retry_extraction(doc_id: int, user=Depends(get_current_user)):
    """Retry extraction for a failed document."""
    doc = get_document(user.id, doc_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    try:
        retry_extraction(user.id, doc_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    # Return updated document
    doc = get_document(user.id, doc_id)
    return _doc_to_public(doc)


@router.post("/api/documents/upload", response_model=List[IngestResultResponse])
async def api_upload(
    request: Request,
    files: List[UploadFile] = File(..., description="One or more files to upload"),
    user=Depends(get_current_user),
):
    """Upload one or more documents for the current user."""
    results: List[IngestResultResponse] = []
    for upload in files:
        original_name = upload.filename
        if not original_name:
            results.append(IngestResultResponse(
                filename="unnamed",
                status="rejected",
                message="File has no name",
                doc_id=None,
                chunk_count=0,
            ))
            continue

        # Read file content, enforcing size limit
        content = await upload.read()
        if len(content) > MAX_FILE_SIZE_BYTES:
            results.append(IngestResultResponse(
                filename=original_name,
                status="rejected",
                message=f"File too large ({(len(content) / 1e6):.1f} MB, limit {(MAX_FILE_SIZE_BYTES / 1e6):.0f} MB)",
                doc_id=None,
                chunk_count=0,
            ))
            continue

        # Process the upload
        result: IngestResult = ingest_upload(user.id, original_name, content)
        results.append(IngestResultResponse(
            filename=original_name,
            status=result.status,
            message=result.message,
            doc_id=result.doc_id,
            chunk_count=result.chunk_count,
        ))

    return results