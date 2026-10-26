"""Document Map service: compute related document links via embedding similarity + shared terms."""

from __future__ import annotations

import json
import logging
import math
import re
from collections import Counter
from typing import Dict, List, Optional, Tuple

import numpy as np

from app.database.repositories import ChunkRepository, DocumentLinkRepository, DocumentRepository
from app.services.vector_service import get_vector_service
from app.utils.config import LINK_MAX_PER_DOC, LINK_MIN_SIMILARITY, LINK_STORE_MIN_SIMILARITY

logger = logging.getLogger(__name__)

# Built-in English stopwords (subset commonly used)
STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "as", "at",
    "be", "because", "been", "before", "being", "below", "between", "both", "but", "by",
    "can", "could",
    "did", "do", "does", "doing", "down", "during",
    "each",
    "few", "for", "from", "further",
    "had", "has", "have", "having", "he", "her", "here", "hers", "herself", "him", "himself", "his", "how",
    "i", "if", "in", "into", "is", "it", "its", "itself",
    "just",
    "me", "more", "most", "my", "myself",
    "no", "nor", "not", "now",
    "of", "off", "on", "once", "only", "or", "other", "our", "ours", "ourselves", "out", "over", "own",
    "s", "same", "she", "should", "so", "some", "such",
    "t", "than", "that", "the", "their", "theirs", "them", "themselves", "then", "there", "these", "they", "this", "those", "through", "to", "too",
    "under", "until", "up",
    "very",
    "was", "we", "were", "what", "when", "where", "which", "while", "who", "whom", "why", "will", "with",
    "you", "your", "yours", "yourself", "yourselves",
}


def _tokenize(text: str) -> List[str]:
    """Lowercase, split on non-letters, drop short tokens, stopwords, pure numbers."""
    tokens = re.split(r"[^a-z]+", text.lower())
    out = []
    for t in tokens:
        if len(t) < 4:
            continue
        if t in STOPWORDS:
            continue
        if t.isdigit():
            continue
        out.append(t)
    return out


def _compute_tfidf(documents: List[Tuple[int, str]]) -> Tuple[Dict[int, Counter], Dict[str, float]]:
    """Compute TF-IDF for a list of (doc_id, content) pairs.

    Returns:
        doc_tf: dict mapping doc_id -> Counter of term -> tf
        idf: dict mapping term -> idf score
    """
    n_docs = len(documents)
    doc_tf: Dict[int, Counter] = {}
    df: Counter = Counter()

    for doc_id, content in documents:
        tokens = _tokenize(content)
        tf = Counter(tokens)
        doc_tf[doc_id] = tf
        for term in set(tokens):
            df[term] += 1

    idf = {term: math.log(n_docs / freq) for term, freq in df.items()}
    return doc_tf, idf


def _get_shared_terms(
    doc_a_id: int,
    doc_b_id: int,
    doc_tf: Dict[int, Counter],
    idf: Dict[str, float],
    max_terms: int = 3,
) -> List[str]:
    """Get top shared terms between two documents by min(tfidf_a, tfidf_b)."""
    tf_a = doc_tf.get(doc_a_id, Counter())
    tf_b = doc_tf.get(doc_b_id, Counter())
    common_terms = set(tf_a.keys()) & set(tf_b.keys())
    if not common_terms:
        return []

    scored = []
    for term in common_terms:
        tfidf_a = tf_a[term] * idf.get(term, 0.0)
        tfidf_b = tf_b[term] * idf.get(term, 0.0)
        scored.append((term, min(tfidf_a, tfidf_b)))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [term for term, _ in scored[:max_terms]]


def get_document_vectors(user_id: int) -> Dict[int, np.ndarray]:
    """Fetch mean L2-normalized embedding vector for each ready document.

    Returns a dict mapping document_id -> vector (numpy array, L2-normalized).
    Skips documents with no chunks in ChromaDB.
    """

    vs = get_vector_service()

    # Get all ready documents for the user
    doc_repo = DocumentRepository()
    docs = doc_repo.list_for_user(user_id)
    ready_docs = [d for d in docs if d.status == "ready"]

    if not ready_docs:
        return {}

    doc_vectors: Dict[int, np.ndarray] = {}

    for doc in ready_docs:
        # Fetch chunk embeddings from ChromaDB filtered by user_id and document_id
        where = {"$and": [{"user_id": user_id}, {"document_id": doc.id}]}
        try:
            res = vs.collection.get(where=where, include=["embeddings"])
            embeddings = res.get("embeddings")
            # ChromaDB may return list or numpy array; check length safely
            if embeddings is None:
                logger.debug("Document %s has no chunk embeddings in ChromaDB", doc.id)
                continue
            if isinstance(embeddings, np.ndarray):
                if embeddings.size == 0:
                    logger.debug("Document %s has no chunk embeddings in ChromaDB", doc.id)
                    continue
            elif not embeddings:
                logger.debug("Document %s has no chunk embeddings in ChromaDB", doc.id)
                continue
            embeddings = np.array(embeddings, dtype=np.float32)
            # Mean of chunk embeddings
            mean_vec = embeddings.mean(axis=0)
            # L2 normalize
            norm = np.linalg.norm(mean_vec)
            if norm > 0:
                doc_vectors[doc.id] = mean_vec / norm
            else:
                logger.debug("Document %s has zero-norm mean embedding", doc.id)
        except Exception as e:
            logger.warning("Failed to fetch embeddings for document %s: %s", doc.id, e)

    return doc_vectors


def compute_links(
    user_id: int,
    min_score: Optional[float] = None,
    max_per_doc: Optional[int] = None,
    use_store_threshold: bool = False,
) -> List[dict]:
    """Compute document links for a user based on embedding similarity.

    Args:
        user_id: The user ID.
        min_score: Minimum cosine similarity threshold (default from config).
        max_per_doc: Maximum neighbors per document (default from config).
        use_store_threshold: If True, use LINK_STORE_MIN_SIMILARITY (0.30) instead of
            LINK_MIN_SIMILARITY (0.45). This is used when rebuilding to store more
            links at a lower floor, filtering at read time.

    Returns:
        List of link dicts with keys: doc_a, doc_b, score, shared_terms.
        Each pair appears once with doc_a < doc_b.
    """
    if min_score is None:
        if use_store_threshold:
            min_score = LINK_STORE_MIN_SIMILARITY
        else:
            min_score = LINK_MIN_SIMILARITY
    if max_per_doc is None:
        max_per_doc = LINK_MAX_PER_DOC

    # 1. Get document vectors
    doc_vectors = get_document_vectors(user_id)
    doc_ids = sorted(doc_vectors.keys())
    n_docs = len(doc_ids)

    if n_docs < 2:
        return []

    # 2. Compute all pairwise cosine similarities
    # Build matrix of vectors
    vec_matrix = np.stack([doc_vectors[doc_id] for doc_id in doc_ids], axis=0)  # (n_docs, dim)
    # Cosine similarity matrix (since vectors are L2-normalized, dot product = cosine)
    sim_matrix = vec_matrix @ vec_matrix.T  # (n_docs, n_docs)

    # 3. For each document, find top max_per_doc neighbors above threshold
    # We keep a pair if score >= min_score AND it's in top-N of at least one doc
    candidate_pairs: Dict[Tuple[int, int], float] = {}

    for i, doc_a in enumerate(doc_ids):
        # Get similarities for this doc (excluding self)
        sims = sim_matrix[i]
        # Get indices of top neighbors (excluding self at i)
        neighbor_indices = np.argsort(sims)[::-1]  # descending
        neighbor_indices = [j for j in neighbor_indices if j != i]

        # Take top max_per_doc
        top_indices = neighbor_indices[:max_per_doc]
        for j in top_indices:
            score = float(sims[j])
            if score >= min_score:
                doc_b = doc_ids[j]
                a, b = (doc_a, doc_b) if doc_a < doc_b else (doc_b, doc_a)
                # Keep the highest score if we see the pair from both sides
                if (a, b) not in candidate_pairs or score > candidate_pairs[(a, b)]:
                    candidate_pairs[(a, b)] = score

    if not candidate_pairs:
        return []

    # 4. Compute shared terms for candidate pairs
    # Fetch document chunk contents for TF-IDF
    chunk_repo = ChunkRepository()
    documents_content: List[Tuple[int, str]] = []
    for doc_id in doc_ids:
        chunks = chunk_repo.list_for_document(doc_id, user_id)
        if chunks:
            full_content = " ".join(c.content for c in chunks)
            documents_content.append((doc_id, full_content))

    if len(documents_content) < 2:
        return []

    doc_tf, idf = _compute_tfidf(documents_content)

    # 5. Build final link list
    links = []
    for (doc_a, doc_b), score in candidate_pairs.items():
        shared_terms = _get_shared_terms(doc_a, doc_b, doc_tf, idf, max_terms=3)
        links.append(
            {
                "doc_a": doc_a,
                "doc_b": doc_b,
                "score": round(score, 4),
                "shared_terms": json.dumps(shared_terms),
            }
        )

    # Sort by score descending
    links.sort(key=lambda x: x["score"], reverse=True)
    return links


def rebuild_links(user_id: int) -> List[dict]:
    """Compute and persist document links for a user in a single transaction.

    Uses LINK_STORE_MIN_SIMILARITY (0.30) as the storage floor, keeping
    top LINK_MAX_PER_DOC neighbors per document. Links are filtered at
    read time using LINK_MIN_SIMILARITY (0.45) by default.

    Returns the list of links that were stored.
    """
    links = compute_links(user_id, use_store_threshold=True)
    link_repo = DocumentLinkRepository()
    link_repo.replace_links_for_user(user_id, links)
    logger.info("Rebuilt %d document links for user %d", len(links), user_id)
    return links