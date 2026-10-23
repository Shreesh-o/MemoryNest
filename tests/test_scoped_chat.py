"""Tests for scoped chat functionality (scoping RAG to chosen document IDs)."""

from __future__ import annotations

import json
import os
import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app
from app.database.database import init_db, get_connection
from app.database.repositories import DocumentRepository, UserRepository
from app.services import chat_service, vector_service, rag_service


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    """Use an isolated temp database and chroma directory for each test."""
    import app.utils.config as config_module
    import app.database.database as db_module

    db_path = tmp_path / "db.sqlite"
    chroma_dir = tmp_path / "chroma"
    upload_dir = tmp_path / "uploads"
    audio_dir = tmp_path / "audio"

    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.setenv("CHROMA_DIR", str(chroma_dir))
    monkeypatch.setenv("UPLOAD_DIR", str(upload_dir))
    monkeypatch.setenv("AUDIO_DIR", str(audio_dir))
    monkeypatch.setenv("MOCK_LLM", "1")

    config_module.refresh_paths()
    db_module.init_db(db_path)

    # Reset vector service singleton so it points to clean test chroma
    vs = vector_service.get_vector_service()
    vs._initialized = False
    vs.__init__()

    yield


@pytest.fixture
def client(temp_db):
    import app.utils.config as config_module
    app = create_app(str(config_module.DB_PATH))
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def user1(client):
    resp = client.post("/api/auth/register", json={"username": "user1", "password": "password123"})
    assert resp.status_code == 201
    resp = client.post("/api/auth/login", json={"username": "user1", "password": "password123"})
    assert resp.status_code == 200
    cookies = dict(resp.cookies)
    user = UserRepository().get_by_username("user1")
    return {"cookies": cookies, "user": user}


@pytest.fixture
def user2(client):
    resp = client.post("/api/auth/register", json={"username": "user2", "password": "password123"})
    assert resp.status_code == 201
    resp = client.post("/api/auth/login", json={"username": "user2", "password": "password123"})
    assert resp.status_code == 200
    cookies = dict(resp.cookies)
    user = UserRepository().get_by_username("user2")
    return {"cookies": cookies, "user": user}


def _seed_document_with_vector(
    user_id: int,
    filename: str,
    content: str,
    status: str = "ready",
    file_type: str | None = None,
) -> int:
    """Helper to insert a document, its chunk, and its vector embedding."""
    from app.database.repositories import DocumentRepository, ChunkRepository
    from app.services.embedding_service import embed_texts

    resolved_type = file_type or (filename.split(".")[-1] if "." in filename else "txt")
    doc_repo = DocumentRepository()
    doc = doc_repo.create(
        user_id=user_id,
        filename=filename,
        stored_path=f"/fake/{filename}",
        file_type=resolved_type,
        size_bytes=len(content),
        status=status,
    )

    if status == "ready":
        doc_repo.set_text(doc.id, user_id, content[:100], 1)

    chunk_repo = ChunkRepository()
    chroma_id = f"{doc.id}_0"
    chunk = chunk_repo.create(
        document_id=doc.id,
        user_id=user_id,
        chunk_index=0,
        content=content,
        token_count=len(content.split()),
        chroma_id=chroma_id,
    )

    if status == "ready":
        emb = embed_texts([content])[0]
        vs = vector_service.get_vector_service()
        vs.add_chunks(
            user_id=user_id,
            document_id=doc.id,
            filename=filename,
            chunks=[{
                "index": 0,
                "text": content,
                "token_count": chunk.token_count,
                "chroma_id": chroma_id,
                "embedding": emb,
            }],
        )

    return doc.id


def test_chat_documents_list_returns_only_ready_documents(client, user1, user2):
    """GET /api/chat/documents returns only ready documents for the authenticated user."""
    # User 1 has two ready docs and one processing doc
    doc1 = _seed_document_with_vector(user1["user"].id, "beta_plan.pdf", "Content of beta plan", status="ready")
    doc2 = _seed_document_with_vector(user1["user"].id, "alpha_specs.docx", "Content of alpha specs", status="ready")
    _seed_document_with_vector(user1["user"].id, "uploading.txt", "Incomplete upload", status="uploaded")

    # User 2 has one ready doc
    _seed_document_with_vector(user2["user"].id, "secret_notes.txt", "User 2 notes", status="ready")

    # Call /api/chat/documents for User 1
    resp = client.get("/api/chat/documents", cookies=user1["cookies"])
    assert resp.status_code == 200
    data = resp.json()

    assert len(data) == 2
    # Verify ordered by filename ascending
    assert data[0]["filename"] == "alpha_specs.docx"
    assert data[0]["id"] == doc2
    assert data[0]["file_type"] == "docx"
    assert data[1]["filename"] == "beta_plan.pdf"
    assert data[1]["id"] == doc1
    assert data[1]["file_type"] == "pdf"


def test_chat_all_documents_default_unchanged(client, user1):
    """Default (no selection sent or null) behaves as all documents with scope='all'."""
    doc1 = _seed_document_with_vector(user1["user"].id, "apples.txt", "Apples are harvested in late October.")
    doc2 = _seed_document_with_vector(user1["user"].id, "bananas.txt", "Bananas grow abundantly in the warm tropics.")

    # 1. No document_ids field sent
    resp = client.post(
        "/api/chat",
        json={"question": "Where do bananas grow?"},
        cookies=user1["cookies"],
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "scope" in data
    assert data["scope"]["scope"] == "all"
    assert data["scope"]["document_ids"] is None
    assert len(data["sources"]) > 0
    assert any(s["document"] == "bananas.txt" for s in data["sources"])

    # 2. Explicit null sent
    resp2 = client.post(
        "/api/chat",
        json={"question": "When are apples harvested?", "document_ids": None},
        cookies=user1["cookies"],
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["scope"]["scope"] == "all"
    assert any(s["document"] == "apples.txt" for s in data2["sources"])


def test_chat_scoped_answer_only_cites_selected_documents(client, user1):
    """Scoped chat only cites selected documents and ignores unselected ones."""
    doc1 = _seed_document_with_vector(user1["user"].id, "apples.txt", "Apples are harvested in late October.")
    doc2 = _seed_document_with_vector(user1["user"].id, "bananas.txt", "Bananas grow abundantly in the warm tropics.")

    # 1. Ask while scoped to doc1: sources only contain doc1, NEVER doc2
    resp1 = client.post(
        "/api/chat",
        json={"question": "Tell me about fruit harvesting seasons.", "document_ids": [doc1]},
        cookies=user1["cookies"],
    )
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["scope"] == {"scope": "selected", "document_ids": [doc1]}
    assert len(data1["sources"]) > 0
    assert all(s["document_id"] == doc1 for s in data1["sources"])
    assert not any(s["document_id"] == doc2 for s in data1["sources"])

    # 2. Ask while scoped to doc2: sources only contain doc2, NEVER doc1
    resp2 = client.post(
        "/api/chat",
        json={"question": "Tell me about fruit harvesting seasons.", "document_ids": [doc2]},
        cookies=user1["cookies"],
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["scope"] == {"scope": "selected", "document_ids": [doc2]}
    assert len(data2["sources"]) > 0
    assert all(s["document_id"] == doc2 for s in data2["sources"])
    assert not any(s["document_id"] == doc1 for s in data2["sources"])


def test_chat_empty_list_returns_422(client, user1):
    """An empty document_ids list returns 422 with 'select at least one document'."""
    resp = client.post(
        "/api/chat",
        json={"question": "Any question", "document_ids": []},
        cookies=user1["cookies"],
    )
    assert resp.status_code == 422
    assert "select at least one document" in resp.json()["detail"].lower()


def test_chat_foreign_id_returns_404_generic_message(client, user1, user2):
    """Passing a document ID owned by another user returns 404 with a generic message."""
    # User 2 owns a document
    doc_user2 = _seed_document_with_vector(user2["user"].id, "private.txt", "User 2 confidential details")

    # User 1 tries to pass User 2's document ID
    resp = client.post(
        "/api/chat",
        json={"question": "Tell me secrets", "document_ids": [doc_user2]},
        cookies=user1["cookies"],
    )
    assert resp.status_code == 404
    detail = resp.json()["detail"].lower()
    assert "not found" in detail
    # Ensure it does not leak that doc_user2 exists for someone else
    assert "user2" not in detail
    assert "foreign" not in detail
    assert "permission" not in detail


def test_chat_unknown_id_returns_404(client, user1):
    """Passing a completely non-existent document ID returns 404 with generic message."""
    resp = client.post(
        "/api/chat",
        json={"question": "Tell me secrets", "document_ids": [999999]},
        cookies=user1["cookies"],
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_chat_not_ready_id_returns_400(client, user1):
    """Passing a document ID that is not ready returns 400 Bad Request."""
    doc_not_ready = _seed_document_with_vector(
        user1["user"].id, "processing.pdf", "Still being extracted", status="processing"
    )

    resp = client.post(
        "/api/chat",
        json={"question": "What is in processing doc?", "document_ids": [doc_not_ready]},
        cookies=user1["cookies"],
    )
    assert resp.status_code == 400
    assert "not ready" in resp.json()["detail"].lower()


def test_chat_cap_list_length_returns_422(client, user1):
    """Exceeding the max document_ids list length (200) returns 422."""
    huge_list = list(range(1, 205))
    resp = client.post(
        "/api/chat",
        json={"question": "Hello", "document_ids": huge_list},
        cookies=user1["cookies"],
    )
    assert resp.status_code == 422
    assert "200" in resp.json()["detail"]


def test_refusal_wording_includes_scope(client, user1):
    """Refusal message says 'selected documents' when scoped, 'stored documents' when unscoped."""
    doc1 = _seed_document_with_vector(user1["user"].id, "apples.txt", "Apples are harvested in late October.")

    # 1. Unscoped question that cannot be found
    resp_unscoped = client.post(
        "/api/chat",
        json={"question": "What is the orbital period of Jupiter?"},
        cookies=user1["cookies"],
    )
    assert resp_unscoped.status_code == 200
    assert "stored documents" in resp_unscoped.json()["answer"].lower()

    # 2. Scoped question that cannot be found in the selection
    resp_scoped = client.post(
        "/api/chat",
        json={"question": "What is the orbital period of Jupiter?", "document_ids": [doc1]},
        cookies=user1["cookies"],
    )
    assert resp_scoped.status_code == 200
    assert "selected documents" in resp_scoped.json()["answer"].lower()


def test_scope_saved_and_returned_in_conversation_history(client, user1):
    """Assistant answer scope is saved in messages table and returned in conversation history."""
    doc1 = _seed_document_with_vector(user1["user"].id, "doc1.txt", "Information alpha.")
    doc2 = _seed_document_with_vector(user1["user"].id, "doc2.txt", "Information beta.")

    # Message 1: scoped to doc1
    resp1 = client.post(
        "/api/chat",
        json={"question": "Question 1", "document_ids": [doc1]},
        cookies=user1["cookies"],
    )
    assert resp1.status_code == 200
    convo_id = resp1.json()["conversation_id"]

    # Message 2: scoped to both doc1 and doc2
    resp2 = client.post(
        "/api/chat",
        json={"question": "Question 2", "conversation_id": convo_id, "document_ids": [doc1, doc2]},
        cookies=user1["cookies"],
    )
    assert resp2.status_code == 200

    # Message 3: unscoped (all)
    resp3 = client.post(
        "/api/chat",
        json={"question": "Question 3", "conversation_id": convo_id},
        cookies=user1["cookies"],
    )
    assert resp3.status_code == 200

    # Verify conversation messages from chat_service directly
    _, messages = chat_service.get_conversation_with_messages(user1["user"].id, convo_id)
    assert len(messages) == 6  # 3 user, 3 assistant

    assistant_msgs = [m for m in messages if m.role == "assistant"]
    assert len(assistant_msgs) == 3

    scope1 = json.loads(assistant_msgs[0].scope)
    assert scope1 == {"scope": "selected", "document_ids": [doc1]}

    scope2 = json.loads(assistant_msgs[1].scope)
    assert scope2 == {"scope": "selected", "document_ids": [doc1, doc2]}

    scope3 = json.loads(assistant_msgs[2].scope)
    assert scope3 == {"scope": "all", "document_ids": None}

    # Verify via API endpoint /api/conversations/{id}
    api_resp = client.get(f"/api/conversations/{convo_id}", cookies=user1["cookies"])
    assert api_resp.status_code == 200
    convo_data = api_resp.json()
    assert "messages" in convo_data
    api_assistant_msgs = [m for m in convo_data["messages"] if m["role"] == "assistant"]
    assert len(api_assistant_msgs) == 3
    assert api_assistant_msgs[0]["scope"] == {"scope": "selected", "document_ids": [doc1]}
    assert api_assistant_msgs[1]["scope"] == {"scope": "selected", "document_ids": [doc1, doc2]}
    assert api_assistant_msgs[2]["scope"] == {"scope": "all", "document_ids": None}

    # Verify via /api/conversations/{id}/messages
    msgs_resp = client.get(f"/api/conversations/{convo_id}/messages", cookies=user1["cookies"])
    assert msgs_resp.status_code == 200
    msgs_list = msgs_resp.json()
    assert len(msgs_list) == 6


def test_scope_migration_idempotent(tmp_path):
    """Ensure _migrate_add_message_scope adds column to old DB without error."""
    import sqlite3
    from app.database.database import _migrate_add_message_scope

    db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(str(db_path))
    # Create messages table without scope column
    conn.execute("""
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            sources TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

    # Check that scope is missing
    cols = [r[1] for r in conn.execute("PRAGMA table_info(messages)").fetchall()]
    assert "scope" not in cols

    # Run migration
    _migrate_add_message_scope(conn)

    # Check that scope now exists
    cols_after = [r[1] for r in conn.execute("PRAGMA table_info(messages)").fetchall()]
    assert "scope" in cols_after

    # Run migration again to verify idempotency
    _migrate_add_message_scope(conn)
    cols_after2 = [r[1] for r in conn.execute("PRAGMA table_info(messages)").fetchall()]
    assert cols_after2 == cols_after
    conn.close()
