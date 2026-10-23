"""Tests for the links API endpoints."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app
from app.database.repositories import (
    DocumentLinkRepository,
    DocumentRepository,
    UserRepository,
)


@pytest.fixture
def client():
    """Create test client with temporary DB."""
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["DB_PATH"] = os.path.join(tmp, "test.db")
        os.environ["CHROMA_DIR"] = os.path.join(tmp, "chroma")
        os.environ["UPLOAD_DIR"] = os.path.join(tmp, "uploads")
        os.environ["AUDIO_DIR"] = os.path.join(tmp, "audio")
        os.environ["MOCK_LLM"] = "1"

        import importlib
        import app.utils.config as config_module
        importlib.reload(config_module)

        from app.database.database import init_db
        init_db()

        app = create_app()
        with TestClient(app) as c:
            yield c


@pytest.fixture
def auth_client(client):
    """Create authenticated client with a user."""
    # Register and login
    client.post("/api/auth/register", json={"username": "testuser", "password": "password123"})
    response = client.post("/api/auth/login", json={"username": "testuser", "password": "password123"})
    assert response.status_code == 200
    return client


@pytest.fixture
def user_with_docs(auth_client):
    """Create a user with some test documents."""
    # Upload a few text documents
    docs = []
    for i, content in enumerate([
        "Machine learning algorithms are used for pattern recognition.",
        "Deep learning neural networks process complex data.",
        "Natural language processing handles text analysis.",
        "Computer vision algorithms detect objects in images.",
    ]):
        response = auth_client.post(
            "/api/documents/upload",
            files={"files": (f"doc{i}.txt", content.encode(), "text/plain")},
        )
        assert response.status_code == 200
        result = response.json()[0]
        assert result["status"] == "ready"
        docs.append(result["doc_id"])
    return docs


class TestGraphEndpoint:
    def test_empty_user(self, auth_client):
        """Empty user returns empty graph."""
        response = auth_client.get("/api/graph")
        assert response.status_code == 200
        data = response.json()
        assert data["nodes"] == []
        assert data["edges"] == []
        assert data["unlinked"] == []

    def test_with_documents_no_links(self, auth_client, user_with_docs):
        """Documents with no links above threshold appear in unlinked."""
        response = auth_client.get("/api/graph?min_score=0.90")
        assert response.status_code == 200
        data = response.json()
        assert len(data["nodes"]) == 0
        assert data["edges"] == []
        assert len(data["unlinked"]) == 4

    def test_min_score_validation_low(self, auth_client):
        """min_score below 0.20 returns 422."""
        response = auth_client.get("/api/graph?min_score=0.10")
        assert response.status_code == 422

    def test_min_score_validation_high(self, auth_client):
        """min_score above 0.95 returns 422."""
        response = auth_client.get("/api/graph?min_score=0.99")
        assert response.status_code == 422

    def test_min_score_default(self, auth_client, user_with_docs, monkeypatch):
        """Default min_score uses LINK_MIN_SIMILARITY (0.45)."""
        from app.utils.config import LINK_MIN_SIMILARITY

        # Mock compute_links to control what's stored
        with patch("app.services.link_service.compute_links") as mock_compute:
            mock_compute.return_value = [
                {"doc_a": 1, "doc_b": 2, "score": 0.50, "shared_terms": '["learning"]'},
                {"doc_a": 2, "doc_b": 3, "score": 0.40, "shared_terms": '["deep"]'},
            ]
            # Need to trigger rebuild
            auth_client.post("/api/graph/refresh")

            response = auth_client.get("/api/graph")
            assert response.status_code == 200
            data = response.json()
            # Only edge with score >= 0.45 should appear
            assert len(data["edges"]) == 1
            assert data["edges"][0]["score"] == 0.50

    def test_user_isolation(self, auth_client):
        """Another user's documents don't appear in graph."""
        # Create another user
        client2 = TestClient(auth_client.app)
        client2.post("/api/auth/register", json={"username": "other", "password": "password123"})
        client2.post("/api/auth/login", json={"username": "other", "password": "password123"})

        # Upload doc for other user
        client2.post(
            "/api/documents/upload",
            files={"files": ("other.txt", b"other content", "text/plain")},
        )

        # Original user's graph should not see other user's docs
        response = auth_client.get("/api/graph")
        assert response.status_code == 200
        data = response.json()
        for node in data["nodes"] + data["unlinked"]:
            assert node["label"] != "other.txt"


class TestRelatedEndpoint:
    def test_404_for_missing_doc(self, auth_client):
        """404 for document not owned by user."""
        response = auth_client.get("/api/documents/999/related")
        assert response.status_code == 404

    def test_404_for_foreign_doc(self, auth_client):
        """404 for document belonging to another user."""
        # Create another user and upload doc
        client2 = TestClient(auth_client.app)
        client2.post("/api/auth/register", json={"username": "other", "password": "password123"})
        client2.post("/api/auth/login", json={"username": "other", "password": "password123"})
        resp = client2.post(
            "/api/documents/upload",
            files={"files": ("other.txt", b"other content", "text/plain")},
        )
        doc_id = resp.json()[0]["doc_id"]

        # Original user tries to access
        response = auth_client.get(f"/api/documents/{doc_id}/related")
        assert response.status_code == 404

    def test_returns_up_to_5_sorted_by_score(self, auth_client, user_with_docs, monkeypatch):
        """Returns up to 5 related docs sorted by score."""
        doc_id = user_with_docs[0]

        with patch("app.services.link_service.compute_links") as mock_compute:
            mock_compute.return_value = [
                {"doc_a": doc_id, "doc_b": d, "score": 0.9 - i * 0.1, "shared_terms": '["test"]'}
                for i, d in enumerate(user_with_docs[1:])
            ]
            auth_client.post("/api/graph/refresh")

            response = auth_client.get(f"/api/documents/{doc_id}/related")
            assert response.status_code == 200
            data = response.json()
            assert len(data["related"]) <= 5
            # Check sorted descending
            scores = [r["score"] for r in data["related"]]
            assert scores == sorted(scores, reverse=True)

    def test_min_score_filter(self, auth_client, user_with_docs, monkeypatch):
        """min_score filters related documents."""
        doc_id = user_with_docs[0]

        with patch("app.services.link_service.compute_links") as mock_compute:
            mock_compute.return_value = [
                {"doc_a": doc_id, "doc_b": user_with_docs[1], "score": 0.60, "shared_terms": '["a"]'},
                {"doc_a": doc_id, "doc_b": user_with_docs[2], "score": 0.40, "shared_terms": '["b"]'},
            ]
            auth_client.post("/api/graph/refresh")

            response = auth_client.get(f"/api/documents/{doc_id}/related?min_score=0.50")
            assert response.status_code == 200
            data = response.json()
            assert len(data["related"]) == 1
            assert data["related"][0]["score"] == 0.60

    def test_min_score_validation(self, auth_client, user_with_docs):
        """min_score validation works on related endpoint."""
        doc_id = user_with_docs[0]
        response = auth_client.get(f"/api/documents/{doc_id}/related?min_score=0.10")
        assert response.status_code == 422


class TestRefreshEndpoint:
    def test_rebuilds_and_returns_counts(self, auth_client, user_with_docs, monkeypatch):
        """Rebuilds links and returns document/edge counts."""
        with patch("app.services.link_service.rebuild_links") as mock_rebuild:
            mock_rebuild.return_value = [
                {"doc_a": 1, "doc_b": 2, "score": 0.5, "shared_terms": '["a"]'},
                {"doc_a": 2, "doc_b": 3, "score": 0.6, "shared_terms": '["b"]'},
            ]
            response = auth_client.post("/api/graph/refresh")
            assert response.status_code == 200
            data = response.json()
            assert data["documents"] == 3
            assert data["edges"] == 2

    def test_user_isolation(self, auth_client):
        """Another user's data not affected."""
        client2 = TestClient(auth_client.app)
        client2.post("/api/auth/register", json={"username": "other", "password": "password123"})
        client2.post("/api/auth/login", json={"username": "other", "password": "password123"})
        client2.post("/api/documents/upload", files={"files": ("o.txt", b"c", "text/plain")})

        # Just verify the refresh works for current user without errors
        response = auth_client.post("/api/graph/refresh")
        assert response.status_code == 200
        data = response.json()
        # Current user has no docs, other user has 1 doc but not visible
        assert data["documents"] == 0
        assert data["edges"] == 0


class TestAutoRebuild:
    def test_rebuild_after_upload(self, auth_client, monkeypatch):
        """Upload triggers link rebuild."""
        with patch("app.api.routers.documents.rebuild_links") as mock_rebuild:
            mock_rebuild.return_value = []
            response = auth_client.post(
                "/api/documents/upload",
                files={"files": ("test.txt", b"new document content", "text/plain")},
            )
            assert response.status_code == 200
            # rebuild_links should have been called
            mock_rebuild.assert_called_once()

    def test_rebuild_failure_does_not_break_upload(self, auth_client, monkeypatch):
        """Rebuild failure doesn't break upload response."""
        with patch("app.api.routers.documents.rebuild_links") as mock_rebuild:
            mock_rebuild.side_effect = Exception("rebuild failed")
            response = auth_client.post(
                "/api/documents/upload",
                files={"files": ("test.txt", b"new document content", "text/plain")},
            )
            assert response.status_code == 200
            assert response.json()[0]["status"] == "ready"

    def test_rebuild_after_delete(self, auth_client, user_with_docs, monkeypatch):
        """Delete triggers link rebuild."""
        doc_id = user_with_docs[0]
        with patch("app.services.document_service.rebuild_links") as mock_rebuild:
            mock_rebuild.return_value = []
            response = auth_client.delete(f"/api/documents/{doc_id}")
            assert response.status_code == 204
            mock_rebuild.assert_called_once()

    def test_rebuild_failure_does_not_break_delete(self, auth_client, user_with_docs, monkeypatch):
        """Rebuild failure doesn't break delete."""
        doc_id = user_with_docs[0]
        with patch("app.api.routers.documents.rebuild_links") as mock_rebuild:
            mock_rebuild.side_effect = Exception("rebuild failed")
            response = auth_client.delete(f"/api/documents/{doc_id}")
            assert response.status_code == 204

    def test_rebuild_after_retry(self, auth_client, user_with_docs, monkeypatch):
        """Retry extraction triggers link rebuild."""
        doc_id = user_with_docs[0]
        # Set doc to error state
        from app.database.repositories import DocumentRepository, UserRepository
        user_repo = UserRepository()
        user = user_repo.get_by_username("testuser")
        doc_repo = DocumentRepository()
        doc_repo.update_status(doc_id, user.id, "error", "test error")

        with patch("app.services.document_service.rebuild_links") as mock_rebuild:
            mock_rebuild.return_value = []
            response = auth_client.post(f"/api/documents/{doc_id}/retry")
            assert response.status_code == 200
            mock_rebuild.assert_called_once()


class TestOldEndpointsGone:
    def test_old_links_endpoint_removed(self, auth_client, user_with_docs):
        """Old /api/documents/{doc_id}/links endpoint should not exist."""
        doc_id = user_with_docs[0]
        response = auth_client.get(f"/api/documents/{doc_id}/links")
        assert response.status_code == 404

    def test_old_rebuild_endpoint_removed(self, auth_client):
        """Old /api/documents/links/rebuild endpoint should not exist."""
        response = auth_client.post("/api/documents/links/rebuild")
        assert response.status_code == 404