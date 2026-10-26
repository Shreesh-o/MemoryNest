"""Documents router: list, get, delete, upload, retry, file, content, html."""

from __future__ import annotations

import logging
import mimetypes
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from app.api.deps import get_current_user
from app.api.schemas import DocumentPublic, IngestResultResponse
from app.services.document_service import delete_document, get_document, list_documents, retry_extraction
from app.services.ingest_service import IngestResult, ingest_upload
from app.services.link_service import rebuild_links
from app.services.text_cache_service import get_cached_html, get_cached_text, invalidate_text_cache
from app.utils.config import MAX_FILE_SIZE_BYTES, UPLOAD_DIR

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
        size_bytes=doc.size_bytes,
        status=doc.status,
        chunk_count=doc.chunk_count,
        error_message=doc.error_message,
        created_at=doc.created_at,
        text_preview=_truncate(doc.text_preview),
    )


def _safe_path(stored_path: str) -> Path:
    """Resolve path and ensure it's inside UPLOAD_DIR (no path traversal)."""
    from app.utils.config import UPLOAD_DIR
    upload_dir = Path(UPLOAD_DIR).resolve()
    file_path = Path(stored_path).resolve()
    # Ensure the file is inside UPLOAD_DIR
    try:
        file_path.relative_to(upload_dir)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return file_path


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
        invalidate_text_cache(doc_id)
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
        invalidate_text_cache(doc_id)
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
    any_success = False
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

        # Check size if reported by headers/spool
        if upload.size is not None and upload.size > MAX_FILE_SIZE_BYTES:
            results.append(IngestResultResponse(
                filename=original_name,
                status="rejected",
                message=f"File too large ({(upload.size / 1e6):.1f} MB, limit {(MAX_FILE_SIZE_BYTES / 1e6):.0f} MB)",
                doc_id=None,
                chunk_count=0,
            ))
            continue

        # Read file content in chunks, aborting early if limit exceeded
        content_buf = bytearray()
        chunk_size = 1024 * 1024  # 1MB
        oversized = False
        while True:
            chunk = await upload.read(chunk_size)
            if not chunk:
                break
            content_buf.extend(chunk)
            if len(content_buf) > MAX_FILE_SIZE_BYTES:
                oversized = True
                break

        if oversized:
            reported_size = upload.size if upload.size and upload.size > len(content_buf) else len(content_buf)
            results.append(IngestResultResponse(
                filename=original_name,
                status="rejected",
                message=f"File too large ({(reported_size / 1e6):.1f} MB, limit {(MAX_FILE_SIZE_BYTES / 1e6):.0f} MB)",
                doc_id=None,
                chunk_count=0,
            ))
            continue

        content = bytes(content_buf)

        # Process the upload in a worker thread to prevent blocking the event loop
        result: IngestResult = await run_in_threadpool(ingest_upload, user.id, original_name, content)
        if result.status == "ready":
            any_success = True
        results.append(IngestResultResponse(
            filename=original_name,
            status=result.status,
            message=result.message,
            doc_id=result.doc_id,
            chunk_count=result.chunk_count,
        ))

    # Rebuild document links once at the end if any document was successfully processed
    if any_success:
        try:
            await run_in_threadpool(rebuild_links, user.id)
        except Exception as e:
            logger.warning("Failed to rebuild document links for user %s after upload: %s", user.id, e)

    return results


@router.get("/api/documents/{doc_id}/file")
def api_get_document_file(
    doc_id: int,
    download: int = Query(0, ge=0, le=1),
    user=Depends(get_current_user),
):
    """Stream the original file from stored_path with correct Content-Type."""
    doc = get_document(user.id, doc_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    file_path = _safe_path(doc.stored_path)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on disk")

    # Determine content type
    content_type, _ = mimetypes.guess_type(str(file_path))
    if not content_type:
        # Fallback based on file_type
        type_map = {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "txt": "text/plain",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
        }
        content_type = type_map.get(doc.file_type.lower(), "application/octet-stream")

    # Content-Disposition
    disposition = "attachment" if download else "inline"
    headers = {
        "Content-Disposition": f'{disposition}; filename="{doc.filename}"',
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "sandbox",
    }

    return FileResponse(
        path=str(file_path),
        media_type=content_type,
        headers=headers,
    )


@router.get("/api/documents/{doc_id}/content")
def api_get_document_content(doc_id: int, user=Depends(get_current_user)):
    """Return extracted text content of the document."""
    doc = get_document(user.id, doc_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if doc.status != "ready":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Document not ready (status: {doc.status})"
        )

    try:
        text, truncated = get_cached_text(doc_id, doc.stored_path, doc.file_type)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on disk")
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Extraction failed: {e}")

    return {
        "text": text,
        "char_count": len(text),
        "truncated": truncated,
        "file_type": doc.file_type,
    }


@router.get("/api/documents/{doc_id}/html")
def api_get_document_html(doc_id: int, user=Depends(get_current_user)):
    """Return DOCX as sanitized HTML (DOCX only)."""
    doc = get_document(user.id, doc_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if doc.file_type.lower() != "docx":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="HTML conversion only supported for DOCX files")

    if doc.status != "ready":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Document not ready (status: {doc.status})"
        )

    try:
        html = get_cached_html(doc_id, doc.stored_path, doc.file_type)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on disk")
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"HTML conversion failed: {e}")

    return {"html": html}