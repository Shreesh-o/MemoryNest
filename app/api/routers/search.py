"""Search router: semantic search over document chunks."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.api.schemas import SearchRequest, SearchResponse
from app.database.models import User
from app.services.search_service import search

router = APIRouter()


@router.post("/api/search", response_model=SearchResponse)
def api_search(
    req: SearchRequest,
    user: User = Depends(get_current_user),
):
    """Semantic search over the current user's documents."""
    try:
        hits = search(user.id, req.query, top_k=req.top_k)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return SearchResponse(
        query=req.query,
        hits=[
            {
                "document_id": h.document_id,
                "filename": h.filename,
                "chunk_index": h.chunk_index,
                "snippet": h.snippet,
                "similarity": round(h.similarity, 3),
            }
            for h in hits
        ],
    )