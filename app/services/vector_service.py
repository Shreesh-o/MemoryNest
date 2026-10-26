"""Vector service: ChromaDB wrapper for document chunks."""

from __future__ import annotations

import chromadb
from chromadb.config import Settings

from app.utils.config import CHROMA_DIR


class VectorService:
    """Thin wrapper around Chroma's PersistentClient with a single collection."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self.client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name="memorynest",
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(
        self,
        user_id: int,
        document_id: int,
        filename: str,
        chunks: list[dict],  # each dict: index, text, token_count, chroma_id
    ) -> None:
        """Add chunks to the collection with metadata for filtering."""
        if not chunks:
            return
        self.collection.add(
            ids=[c["chroma_id"] for c in chunks],
            documents=[c["text"] for c in chunks],
            embeddings=[c["embedding"] for c in chunks],
            metadatas=[
                {
                    "user_id": int(user_id),
                    "document_id": int(document_id),
                    "filename": filename,
                    "chunk_index": c["index"],
                    "token_count": c["token_count"],
                }
                for c in chunks
            ],
        )

    def query(
        self,
        user_id: int,
        query_embedding: list[float],
        top_k: int = 5,
        document_ids: list[int] | None = None,
    ) -> list[dict]:
        """Query similar chunks, filtered by user_id and optionally document_ids.

        Returns list of dicts with keys: chroma_id, text, metadata, similarity (1 - distance).
        """
        if top_k <= 0:
            return []

        if document_ids is not None:
            where = {
                "$and": [
                    {"user_id": int(user_id)},
                    {"document_id": {"$in": [int(d) for d in document_ids]}},
                ]
            }
        else:
            where = {"user_id": int(user_id)}

        res = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        out = []
        if not res["ids"] or not res["ids"][0]:
            return out
        for i, cid in enumerate(res["ids"][0]):
            dist = res["distances"][0][i]
            similarity = 1.0 - dist  # cosine distance -> similarity
            out.append(
                {
                    "chroma_id": cid,
                    "text": res["documents"][0][i],
                    "metadata": res["metadatas"][0][i],
                    "similarity": similarity,
                }
            )
        return out

    def delete_document(self, document_id: int, user_id: int) -> None:
        """Delete all vectors of a document (and user).

        Retries once. Raises RuntimeError if the vectors could not be removed,
        so callers never report success while vectors remain.
        """
        import logging

        logger = logging.getLogger(__name__)
        where = {"$and": [{"document_id": document_id}, {"user_id": user_id}]}
        last_error = None
        for attempt in range(2):
            try:
                res = self.collection.get(where=where, include=[])
                if not res["ids"]:
                    return  # nothing to delete
                self.collection.delete(ids=res["ids"])
                return
            except Exception as e:
                last_error = e
                logger.warning(
                    "Chroma delete attempt %d failed for doc %s", attempt + 1, document_id
                )
        logger.error(
            "Chroma vector cleanup incomplete for doc %s; run scripts/repair.py --fix",
            document_id,
            exc_info=last_error,
        )
        raise RuntimeError(
            f"Vector cleanup incomplete for document {document_id}; "
            "run scripts/repair.py --fix"
        ) from last_error

    def delete_user(self, user_id: int) -> None:
        """Delete all chunks for a user."""
        res = self.collection.get(where={"user_id": user_id}, include=[])
        if res["ids"]:
            self.collection.delete(ids=res["ids"])


def get_vector_service() -> VectorService:
    return VectorService()