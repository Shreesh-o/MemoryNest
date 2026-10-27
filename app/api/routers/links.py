"""Links router: Document Map graph endpoints."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_current_user
from app.api.schemas import GraphEdge, GraphNode, GraphRefreshResponse, GraphResponse, RelatedDocument, RelatedResponse
from app.database.repositories import DocumentLinkRepository, DocumentRepository
from app.services import link_service

logger = logging.getLogger(__name__)

router = APIRouter()


def _doc_to_graph_node(doc, link_count: int = 0):
    """Convert a document to a GraphNode."""
    return GraphNode(
        id=doc.id,
        label=doc.filename,
        file_type=doc.file_type,
        link_count=link_count,
    )


@router.get("/api/graph", response_model=GraphResponse)
def api_get_graph(
    min_score: float | None = Query(
        default=None,
        ge=0.20,
        le=0.95,
        description="Minimum similarity score for edges (0.20-0.95)",
    ),
    user=Depends(get_current_user),
):
    """Get the Document Map graph for the current user.

    Returns nodes (documents with at least one edge above min_score),
    edges (stored links with score >= min_score), and unlinked documents
    (no edges above min_score).

    min_score defaults to LINK_MIN_SIMILARITY (0.45).
    """
    from app.utils.config import LINK_MIN_SIMILARITY

    if min_score is None:
        min_score = LINK_MIN_SIMILARITY

    # Get all ready documents for the user
    doc_repo = DocumentRepository()
    docs = doc_repo.list_for_user(user.id)
    ready_docs = [d for d in docs if d.status == "ready"]

    if not ready_docs:
        return GraphResponse(nodes=[], edges=[], unlinked=[])

    # Get all stored links for the user
    link_repo = DocumentLinkRepository()
    all_links = link_repo.list_links(user.id)

    # If no links stored yet and user has >= 2 ready documents, auto-rebuild
    if not all_links and len(ready_docs) >= 2:
        try:
            link_service.rebuild_links(user.id)
            all_links = link_repo.list_links(user.id)
        except Exception as e:
            logger.warning("Auto-rebuilding links on graph fetch failed for user %s: %s", user.id, e)

    # Filter edges by min_score
    filtered_edges = [link for link in all_links if link.score >= min_score]

    # Compute link_count per document from filtered edges
    link_count: dict[int, int] = {}
    for link in filtered_edges:
        link_count[link.doc_a] = link_count.get(link.doc_a, 0) + 1
        link_count[link.doc_b] = link_count.get(link.doc_b, 0) + 1

    # Build nodes and unlinked
    nodes = []
    unlinked = []
    for doc in ready_docs:
        count = link_count.get(doc.id, 0)
        node = _doc_to_graph_node(doc, count)
        if count > 0:
            nodes.append(node)
        else:
            unlinked.append(node)

    # Build edges response
    edges = []
    for link in filtered_edges:
        shared = json.loads(link.shared_terms) if link.shared_terms else []
        edges.append(GraphEdge(
            source=link.doc_a,
            target=link.doc_b,
            score=link.score,
            shared_terms=shared,
        ))

    return GraphResponse(nodes=nodes, edges=edges, unlinked=unlinked)


@router.get("/api/documents/{doc_id}/related", response_model=RelatedResponse)
def api_get_related(
    doc_id: int,
    min_score: float | None = Query(
        default=None,
        ge=0.20,
        le=0.95,
        description="Minimum similarity score (0.20-0.95)",
    ),
    user=Depends(get_current_user),
):
    """Get up to 5 related documents for a specific document.

    Returns list of {id, filename, file_type, score, shared_terms}
    sorted by score descending. 404 if document not found or not owned.
    """
    from app.utils.config import LINK_MIN_SIMILARITY

    if min_score is None:
        min_score = LINK_MIN_SIMILARITY

    # Verify document belongs to user and is ready
    doc_repo = DocumentRepository()
    doc = doc_repo.get_by_id(doc_id, user.id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if doc.status != "ready":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Document not ready (status: {doc.status})"
        )

    # Get links for this document
    link_repo = DocumentLinkRepository()
    links = link_repo.list_links_for_document(user.id, doc_id)

    # Filter by min_score and build response
    related = []
    for link in links:
        if link.score < min_score:
            continue
        other_id = link.doc_b if link.doc_a == doc_id else link.doc_a
        other_doc = doc_repo.get_by_id(other_id, user.id)
        if other_doc and other_doc.status == "ready":
            shared = json.loads(link.shared_terms) if link.shared_terms else []
            related.append(RelatedDocument(
                id=other_doc.id,
                filename=other_doc.filename,
                file_type=other_doc.file_type,
                score=link.score,
                shared_terms=shared,
            ))

    # Sort by score descending and limit to 5
    related.sort(key=lambda x: x.score, reverse=True)
    related = related[:5]

    return RelatedResponse(related=related)


@router.post("/api/graph/refresh", response_model=GraphRefreshResponse)
def api_refresh_graph(user=Depends(get_current_user)):
    """Rebuild the Document Map for the current user.

    Returns counts of documents and edges stored.
    """
    links = link_service.rebuild_links(user.id)

    # Count unique documents involved in links
    doc_ids = set()
    for link in links:
        doc_ids.add(link["doc_a"])
        doc_ids.add(link["doc_b"])

    return GraphRefreshResponse(documents=len(doc_ids), edges=len(links))