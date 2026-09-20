"""Tests for RAG pipeline (mock LLM)."""

from __future__ import annotations

import os

import pytest

from app.services import rag_service, vector_service, embedding_service
from app.database.repositories import DocumentRepository, ChunkRepository
from app.database.database import init_db
from app.utils.config import CHROMA_DIR


@pytest.fixture(autouse=True)
def mock_llm(monkeypatch):
    monkeypatch.setenv("MOCK_LLM", "1")


@pytest.fixture(scope="function")
def rag_setup(tmp_path, monkeypatch):
    """Set up a clean Chroma DB and add some test chunks."""
    test_chroma = tmp_path / "chroma_rag"
    monkeypatch.setattr("app.services.vector_service.CHROMA_DIR", test_chroma)

    # Reinit vector service
    vs = vector_service.VectorService()
    vs.client = None
    vs._initialized = False
    vs.__init__()

    # Add test docs for user 1
    texts = [
        "The quarterly revenue was $1.2M, up 12% from last quarter.",
        "The board meeting is scheduled for October 15, 2026 at 9:00 AM.",
        "Project launch is planned for March 3, 2027.",
    ]
    embs = embedding_service.embed_texts(texts)
    vs.add_chunks(
        user_id=1,
        document_id=10,
        filename="report.pdf",
        chunks=[
            {"index": 0, "text": texts[0], "token_count": 20, "chroma_id": "c0", "embedding": embs[0]},
            {"index": 1, "text": texts[1], "token_count": 20, "chroma_id": "c1", "embedding": embs[1]},
            {"index": 2, "text": texts[2], "token_count": 20, "chroma_id": "c2", "embedding": embs[2]},
        ],
    )
    return vs


def test_rag_answer_above_threshold(rag_setup):
    result = rag_service.rag_answer(1, "What was the quarterly revenue?")
    assert result.below_threshold is False
    assert "mock" in result.answer.lower() or "$1.2" in result.answer or "revenue" in result.answer.lower()
    assert len(result.sources) >= 1
    assert result.sources[0]["document"] == "report.pdf"


def test_rag_answer_below_threshold(rag_setup):
    # Unrelated query should fall below similarity threshold
    result = rag_service.rag_answer(1, "What is the capital of France?")
    assert result.below_threshold is True
    assert "couldn't find" in result.answer.lower()
    assert result.sources == []


def test_rag_user_isolation(rag_setup):
    # Add doc for user 2
    texts = ["User two secret data"]
    embs = embedding_service.embed_texts(texts)
    rag_setup.add_chunks(
        user_id=2,
        document_id=20,
        filename="secret.txt",
        chunks=[{"index": 0, "text": texts[0], "token_count": 5, "chroma_id": "uc0", "embedding": embs[0]}],
    )

    # User 1 should not see user 2's data
    result = rag_service.rag_answer(1, "secret data")
    assert result.below_threshold or all(s["document"] != "secret.txt" for s in result.sources)


def test_rag_empty_db():
    os.environ["MOCK_LLM"] = "1"
    # No chunks added
    result = rag_service.rag_answer(999, "anything")
    assert result.below_threshold is True
    assert "couldn't find" in result.answer.lower()
    assert result.sources == []