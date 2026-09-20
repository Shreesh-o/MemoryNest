"""Tests for embedding and vector services."""

from __future__ import annotations

import pytest

from app.services import embedding_service, vector_service
from app.database.repositories import DocumentRepository, ChunkRepository
from app.database.database import init_db
from app.utils.config import CHROMA_DIR


@pytest.fixture(scope="module")
def embed_model():
    # Force model load once
    return embedding_service._get_model()


def test_embed_texts(embed_model):
    vecs = embedding_service.embed_texts(["hello world", "test document"])
    assert len(vecs) == 2
    assert len(vecs[0]) == 384  # all-MiniLM-L6-v2 dimension
    assert len(vecs[1]) == 384


def test_embed_query(embed_model):
    v = embedding_service.embed_query("what is this?")
    assert len(v) == 384


def test_vector_service_roundtrip(tmp_path, monkeypatch):
    # Use isolated chroma dir
    test_chroma = tmp_path / "chroma_test"
    monkeypatch.setattr("app.services.vector_service.CHROMA_DIR", test_chroma)

    vs = vector_service.VectorService()
    vs.client = None  # force reinit with new path
    vs._initialized = False
    vs.__init__()

    user_id = 1
    doc_id = 42
    # Generate embeddings
    texts = ["first chunk text", "second chunk content", "third piece here"]
    embeddings = embedding_service.embed_texts(texts)
    chunks = [
        {"index": 0, "text": texts[0], "token_count": 10, "chroma_id": "c0", "embedding": embeddings[0]},
        {"index": 1, "text": texts[1], "token_count": 12, "chroma_id": "c1", "embedding": embeddings[1]},
        {"index": 2, "text": texts[2], "token_count": 8, "chroma_id": "c2", "embedding": embeddings[2]},
    ]
    vs.add_chunks(user_id, doc_id, "test.txt", chunks)

    # Query
    q_emb = embedding_service.embed_query("chunk content")
    results = vs.query(user_id, q_emb, top_k=2)
    assert len(results) == 2
    assert results[0]["similarity"] > results[1]["similarity"]
    assert "second" in results[0]["text"]

    # Different user gets nothing
    results2 = vs.query(999, q_emb, top_k=5)
    assert results2 == []

    # Delete document
    vs.delete_document(doc_id, user_id)
    results3 = vs.query(user_id, q_emb, top_k=5)
    assert results3 == []


def test_vector_delete_user(tmp_path, monkeypatch):
    test_chroma = tmp_path / "chroma_test2"
    monkeypatch.setattr("app.services.vector_service.CHROMA_DIR", test_chroma)

    vs = vector_service.VectorService()
    vs.client = None
    vs._initialized = False
    vs.__init__()

    texts = ["user one doc", "user two doc"]
    embs = embedding_service.embed_texts(texts)
    vs.add_chunks(1, 1, "a.txt", [{"index": 0, "text": texts[0], "token_count": 5, "chroma_id": "u1c0", "embedding": embs[0]}])
    vs.add_chunks(2, 1, "b.txt", [{"index": 0, "text": texts[1], "token_count": 5, "chroma_id": "u2c0", "embedding": embs[1]}])

    assert len(vs.query(1, embs[0], top_k=5)) == 1
    assert len(vs.query(2, embs[1], top_k=5)) == 1

    vs.delete_user(1)
    assert vs.query(1, embs[0], top_k=5) == []
    assert len(vs.query(2, embs[1], top_k=5)) == 1