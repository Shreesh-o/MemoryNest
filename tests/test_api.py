"""Tests for the FastAPI layer (auth, documents, upload, health)."""

from __future__ import annotations

import os
import tempfile
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

# These tests rely on the autouse test_storage fixture in conftest.py
# which sets up temp DB, Chroma, uploads dirs and MOCK_LLM=1


@pytest.fixture
def client():
    """FastAPI TestClient with the app."""
    # Must import after env vars are set by test_storage fixture
    from app.api.main import app
    return TestClient(app)


@pytest.fixture
def temp_db():
    """Fresh per-test DB from the autouse test_storage fixture."""
    import app.utils.config as config_module
    return config_module.DB_PATH


@pytest.fixture
def temp_chroma():
    """Per-test Chroma dir from the autouse test_storage fixture."""
    import app.utils.config as config_module
    return config_module.CHROMA_DIR


@pytest.fixture
def temp_uploads():
    """Per-test upload dir from the autouse test_storage fixture."""
    import app.utils.config as config_module
    config_module.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    return config_module.UPLOAD_DIR


@pytest.fixture
def test_user(temp_db):
    """Create a test user via auth_service."""
    from app.services.auth_service import register
    return register("testuser", "password123", "test@example.com")


def _register_and_login(client, username="testuser", password="password123", email="test@example.com"):
    """Helper: register and login, returning the response from login."""
    client.post("/api/auth/register", json={"username": username, "password": password, "email": email})
    resp = client.post("/api/auth/login", json={"username": username, "password": password})
    return resp


class TestAuth:
    """Tests for authentication endpoints."""

    def test_register_success(self, client):
        """Register returns the public user without password hash."""
        resp = client.post("/api/auth/register", json={
            "username": "newuser",
            "password": "password123",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["username"] == "newuser"
        assert "password_hash" not in data
        assert "password" not in data

    def test_login_me(self, client):
        """Register -> login -> me returns the user."""
        _register_and_login(client)
        resp = client.get("/api/auth/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "testuser"
        assert "password_hash" not in data

    def test_login_cookie_max_age_matches_jwt_expire(self, client):
        """Login cookie Max-Age aligns with JWT_EXPIRE_MINUTES."""
        from app.utils.config import JWT_EXPIRE_MINUTES
        resp = _register_and_login(client, username="cookietest", password="password123")
        assert resp.status_code == 200
        set_cookie = resp.headers.get("set-cookie", "")
        expected_max_age = f"Max-Age={JWT_EXPIRE_MINUTES * 60}"
        assert expected_max_age.lower() in set_cookie.lower(), f"Expected {expected_max_age} in Set-Cookie header: {set_cookie}"


    def test_login_wrong_password(self, client):
        """Wrong password returns 401."""
        client.post("/api/auth/register", json={
            "username": "wrongpw",
            "password": "password123",
        })
        resp = client.post("/api/auth/login", json={
            "username": "wrongpw",
            "password": "wrongpassword",
        })
        assert resp.status_code == 401

    def test_register_duplicate_409(self, client):
        """Duplicate username returns 409."""
        client.post("/api/auth/register", json={
            "username": "duplicate",
            "password": "password123",
        })
        resp = client.post("/api/auth/register", json={
            "username": "duplicate",
            "password": "password123",
        })
        assert resp.status_code == 409

    def test_register_short_password_400(self, client):
        """Short password returns 400."""
        resp = client.post("/api/auth/register", json={
            "username": "shortpw",
            "password": "12345",
        })
        assert resp.status_code == 400

    def test_protected_endpoints_401_without_cookie(self, client):
        """All protected endpoints return 401 without a cookie."""
        assert client.get("/api/documents").status_code == 401
        assert client.get("/api/documents/1").status_code == 401
        assert client.delete("/api/documents/1").status_code == 401
        assert client.post("/api/documents/upload").status_code == 401
        assert client.patch("/api/auth/me/email", json={"email": "a@b.com"}).status_code == 401

    def test_logout_clears_cookie(self, client):
        """Logout clears the session cookie."""
        _register_and_login(client)
        # Verify authenticated
        assert client.get("/api/auth/me").status_code == 200
        # Logout
        resp = client.post("/api/auth/logout")
        assert resp.status_code == 200
        # Should be unauthenticated now
        client.cookies.clear()
        assert client.get("/api/auth/me").status_code == 401

    def test_password_hash_never_in_response(self, client):
        """Password hash never appears in any response."""
        client.post("/api/auth/register", json={
            "username": "nohash",
            "password": "password123",
        })
        resp = client.post("/api/auth/login", json={
            "username": "nohash",
            "password": "password123",
        })
        # Check all response bodies
        for body in [resp.json(), client.get("/api/auth/me").json()]:
            assert "password_hash" not in str(body)
            assert "password" not in str(body).lower() or "password123" not in str(body)

    def test_update_email_success_and_normalization(self, client):
        """PATCH /api/auth/me/email updates email and normalizes to lowercase."""
        _register_and_login(client, username="emailuser", password="password123", email=None)
        # Check GET /api/auth/me initially returns email null
        me_resp = client.get("/api/auth/me")
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] is None

        # Update email with mixed case
        patch_resp = client.patch("/api/auth/me/email", json={"email": "EmailUser@Example.COM"})
        assert patch_resp.status_code == 200
        assert patch_resp.json()["email"] == "emailuser@example.com"

        # Verify GET /api/auth/me returns updated email
        me_resp2 = client.get("/api/auth/me")
        assert me_resp2.status_code == 200
        assert me_resp2.json()["email"] == "emailuser@example.com"

    def test_update_email_invalid_format(self, client):
        """PATCH /api/auth/me/email with invalid email returns 400."""
        _register_and_login(client)
        resp = client.patch("/api/auth/me/email", json={"email": "not-an-email"})
        assert resp.status_code == 400
        assert "email" in resp.json()["detail"].lower()

    def test_update_email_duplicate_rejected(self, client):
        """Updating email to one already used by another user returns 409."""
        # Register user 1 with email
        client.post("/api/auth/register", json={
            "username": "userone",
            "password": "password123",
            "email": "userone@example.com",
        })
        # Register and login user 2
        client.post("/api/auth/register", json={
            "username": "usertwo",
            "password": "password123",
        })
        client.post("/api/auth/login", json={
            "username": "usertwo",
            "password": "password123",
        })

        # User 2 tries to use user 1's email (case-insensitive)
        resp = client.patch("/api/auth/me/email", json={"email": "USERONE@EXAMPLE.COM"})
        assert resp.status_code == 409
        assert "already taken" in resp.json()["detail"].lower()

    def test_update_email_same_email_allowed(self, client):
        """Updating to the user's own existing email succeeds."""
        _register_and_login(client, username="sameemail", password="password123", email="same@example.com")
        resp = client.patch("/api/auth/me/email", json={"email": "SAME@EXAMPLE.COM"})
        assert resp.status_code == 200
        assert resp.json()["email"] == "same@example.com"

    def test_update_email_unset_cases(self, client):
        """PATCH /api/auth/me/email unsets email when null or empty string is sent."""
        _register_and_login(client, username="unsetuser", password="password123", email="unset@example.com")
        # Check initially set
        assert client.get("/api/auth/me").json()["email"] == "unset@example.com"

        # Unset with null
        resp = client.patch("/api/auth/me/email", json={"email": None})
        assert resp.status_code == 200
        assert resp.json()["email"] is None
        assert client.get("/api/auth/me").json()["email"] is None

        # Re-set
        client.patch("/api/auth/me/email", json={"email": "reset@example.com"})
        assert client.get("/api/auth/me").json()["email"] == "reset@example.com"

        # Unset with empty string
        resp2 = client.patch("/api/auth/me/email", json={"email": ""})
        assert resp2.status_code == 200
        assert resp2.json()["email"] is None
        assert client.get("/api/auth/me").json()["email"] is None

    def test_user_can_only_change_own_email(self, client):
        """User A and User B cannot affect each other's email."""
        # Register user A and user B
        client.post("/api/auth/register", json={
            "username": "usera",
            "password": "password123",
            "email": "usera@example.com",
        })
        client.post("/api/auth/register", json={
            "username": "userb",
            "password": "password123",
            "email": "userb@example.com",
        })

        # Login as user B and change email
        client.post("/api/auth/login", json={"username": "userb", "password": "password123"})
        patch_b = client.patch("/api/auth/me/email", json={"email": "new_userb@example.com"})
        assert patch_b.status_code == 200
        assert patch_b.json()["email"] == "new_userb@example.com"

        # Login as user A and verify user A's email is untouched
        client.post("/api/auth/login", json={"username": "usera", "password": "password123"})
        me_a = client.get("/api/auth/me")
        assert me_a.status_code == 200
        assert me_a.json()["email"] == "usera@example.com"

    def test_register_with_email_validation(self, client):
        """Register validates email and saves normalized lowercase."""
        # Invalid email at registration
        bad_resp = client.post("/api/auth/register", json={
            "username": "bademailreg",
            "password": "password123",
            "email": "not-valid-email",
        })
        assert bad_resp.status_code == 400

        # Valid email normalized
        good_resp = client.post("/api/auth/register", json={
            "username": "goodemailreg",
            "password": "password123",
            "email": "Good.Email@Domain.COM",
        })
        assert good_resp.status_code == 201
        assert good_resp.json()["email"] == "good.email@domain.com"

        # Duplicate email at registration rejected with 409
        dup_resp = client.post("/api/auth/register", json={
            "username": "dupemailreg",
            "password": "password123",
            "email": "good.email@domain.com",
        })
        assert dup_resp.status_code == 409


class TestDocuments:
    """Tests for document endpoints."""

    def test_upload_txt_with_future_date(self, client, temp_db, temp_chroma, temp_uploads):
        """Upload a TXT with a future date -> result 'ready'."""
        _register_and_login(client)

        # Compute a deadline date that is 10 days in the future
        due = date.today() + timedelta(days=10)
        deadline_str = f"{due.day} {due.strftime('%B %Y')}"
        txt_content = f"Submission deadline: {deadline_str}"
        file_bytes = txt_content.encode("utf-8")

        resp = client.post(
            "/api/documents/upload",
            files={"files": ("test.txt", file_bytes, "text/plain")},
        )
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) == 1
        assert results[0]["status"] == "ready"
        assert results[0]["doc_id"] is not None
        assert results[0]["chunk_count"] > 0

    def test_list_shows_uploaded_document(self, client, temp_db, temp_chroma, temp_uploads):
        """List shows the uploaded document."""
        _register_and_login(client)

        due = date.today() + timedelta(days=10)
        deadline_str = f"{due.day} {due.strftime('%B %Y')}"
        txt_content = f"Deadline: {deadline_str}"
        file_bytes = txt_content.encode("utf-8")

        client.post(
            "/api/documents/upload",
            files={"files": ("doc.txt", file_bytes, "text/plain")},
        )

        resp = client.get("/api/documents")
        assert resp.status_code == 200
        docs = resp.json()
        assert len(docs) >= 1
        assert any(d["filename"] == "doc.txt" for d in docs)

    def test_get_document(self, client, temp_db, temp_chroma, temp_uploads):
        """Get a specific document by ID."""
        _register_and_login(client)

        due = date.today() + timedelta(days=10)
        deadline_str = f"{due.day} {due.strftime('%B %Y')}"
        txt_content = f"Deadline: {deadline_str}"
        file_bytes = txt_content.encode("utf-8")

        resp = client.post(
            "/api/documents/upload",
            files={"files": ("myfile.txt", file_bytes, "text/plain")},
        )
        doc_id = resp.json()[0]["doc_id"]

        resp = client.get(f"/api/documents/{doc_id}")
        assert resp.status_code == 200
        doc = resp.json()
        assert doc["filename"] == "myfile.txt"
        assert "stored_path" not in str(doc)
        assert "/uploads/" not in str(doc)

    def test_upload_duplicate(self, client, temp_db, temp_chroma, temp_uploads):
        """Same file twice -> second is 'duplicate'."""
        _register_and_login(client)

        txt_content = "This is a test document for duplicate detection."
        file_bytes = txt_content.encode("utf-8")

        resp1 = client.post(
            "/api/documents/upload",
            files={"files": ("test.txt", file_bytes, "text/plain")},
        )
        assert resp1.json()[0]["status"] == "ready"

        resp2 = client.post(
            "/api/documents/upload",
            files={"files": ("test.txt", file_bytes, "text/plain")},
        )
        assert resp2.json()[0]["status"] == "duplicate"

    def test_upload_streaming_size_limit_rejection(self, client, temp_db, temp_chroma, temp_uploads):
        """Streaming or oversized upload is rejected safely when exceeding limit."""
        _register_and_login(client)
        from app.utils.config import MAX_FILE_SIZE_BYTES

        oversized_bytes = b"x" * (MAX_FILE_SIZE_BYTES + 1024)
        resp = client.post(
            "/api/documents/upload",
            files={"files": ("large.txt", oversized_bytes, "text/plain")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["status"] == "rejected"
        assert "too large" in data[0]["message"].lower()

    def test_upload_binary_pdf_rejected(self, client, temp_db, temp_chroma, temp_uploads):
        """Random binary named .pdf -> 'rejected'."""
        _register_and_login(client)

        file_bytes = os.urandom(512)

        resp = client.post(
            "/api/documents/upload",
            files={"files": ("corrupt.pdf", file_bytes, "application/pdf")},
        )
        assert resp.json()[0]["status"] == "rejected"

    def test_upload_batch_mixed(self, client, temp_db, temp_chroma, temp_uploads):
        """Batch with one bad file and one good file -> both reported."""
        _register_and_login(client)

        due = date.today() + timedelta(days=10)
        deadline_str = f"{due.day} {due.strftime('%B %Y')}"
        good_content = f"Deadline: {deadline_str}".encode("utf-8")
        bad_content = b"\x00\x01\x02binary"

        resp = client.post(
            "/api/documents/upload",
            files=[
                ("files", ("bad.pdf", bad_content, "application/pdf")),
                ("files", ("good.txt", good_content, "text/plain")),
            ],
        )
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) == 2
        statuses = {r["filename"]: r["status"] for r in results}
        assert statuses["bad.pdf"] == "rejected"
        assert statuses["good.txt"] == "ready"


class TestDocumentIsolation:
    """Tests for user isolation."""

    def test_user_b_cannot_see_user_a_docs(self, client, temp_db, temp_chroma, temp_uploads):
        """User B gets 404 on user A's document and doesn't see it in list."""
        # User A uploads
        _register_and_login(client, "usera", "password1", "a@example.com")
        due = date.today() + timedelta(days=10)
        deadline_str = f"{due.day} {due.strftime('%B %Y')}"
        txt_content = f"Deadline: {deadline_str}"
        file_bytes = txt_content.encode("utf-8")

        resp = client.post(
            "/api/documents/upload",
            files={"files": ("secret.txt", file_bytes, "text/plain")},
        )
        doc_id = resp.json()[0]["doc_id"]

        # User B registers and logs in
        client.cookies.clear()
        _register_and_login(client, "userb", "password2", "b@example.com")

        # User B should not see the document in list
        resp = client.get("/api/documents")
        docs = resp.json()
        doc_ids = [d["id"] for d in docs]
        assert doc_id not in doc_ids

        # User B should get 404 for user A's document
        resp = client.get(f"/api/documents/{doc_id}")
        assert resp.status_code == 404

        # User B should not be able to delete user A's document
        resp = client.delete(f"/api/documents/{doc_id}")
        assert resp.status_code == 404

    def test_delete_204_then_404(self, client, temp_db, temp_chroma, temp_uploads):
        """Delete returns 204, then 404."""
        _register_and_login(client)

        due = date.today() + timedelta(days=10)
        deadline_str = f"{due.day} {due.strftime('%B %Y')}"
        txt_content = f"Deadline: {deadline_str}"
        file_bytes = txt_content.encode("utf-8")

        resp = client.post(
            "/api/documents/upload",
            files={"files": ("todelete.txt", file_bytes, "text/plain")},
        )
        doc_id = resp.json()[0]["doc_id"]

        # Delete
        resp = client.delete(f"/api/documents/{doc_id}")
        assert resp.status_code == 204

        # Verify file and vectors are gone
        from app.database.repositories import DocumentRepository, ChunkRepository
        from app.services import vector_service
        from pathlib import Path

        doc_repo = DocumentRepository()
        assert doc_repo.get_by_id(doc_id, 1) is None

        chunk_repo = ChunkRepository()
        assert len(chunk_repo.list_for_document(doc_id, 1)) == 0

        vs = vector_service.get_vector_service()
        results = vs.collection.get(where={"document_id": doc_id}, include=[])
        assert len(results["ids"]) == 0

        # Second delete -> 404
        resp = client.delete(f"/api/documents/{doc_id}")
        assert resp.status_code == 404


class TestVectorDeleteFailure:
    """Tests for vector delete failure handling."""

    def test_delete_vector_failure_returns_409(self, client, temp_db, temp_chroma, temp_uploads, monkeypatch):
        """Delete when vector deletion fails returns 409 and document still exists."""
        _register_and_login(client)

        due = date.today() + timedelta(days=10)
        deadline_str = f"{due.day} {due.strftime('%B %Y')}"
        txt_content = f"Deadline: {deadline_str}"
        file_bytes = txt_content.encode("utf-8")

        resp = client.post(
            "/api/documents/upload",
            files={"files": ("fail_delete.txt", file_bytes, "text/plain")},
        )
        doc_id = resp.json()[0]["doc_id"]

        # Monkeypatch vector service to raise RuntimeError
        from app.services import vector_service

        def boom(self, doc_id, user_id):
            raise RuntimeError("vector cleanup failed")

        monkeypatch.setattr(vector_service.VectorService, "delete_document", boom)

        resp = client.delete(f"/api/documents/{doc_id}")
        assert resp.status_code == 409

        # Document should still exist
        from app.database.repositories import DocumentRepository
        doc = DocumentRepository().get_by_id(doc_id, 1)
        assert doc is not None


class TestHealth:
    """Tests for health endpoint."""

    def test_health_no_auth(self, client):
        """Health check returns ok without auth."""
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "ollama" in data
        assert "mock_llm" in data
        assert "tts_engine" in data