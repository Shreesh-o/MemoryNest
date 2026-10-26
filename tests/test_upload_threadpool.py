"""Test for ARC-02: Document upload offloading to worker threadpool."""

from __future__ import annotations

import threading
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app
from app.utils.config import DB_PATH


@pytest.fixture
def client():
    app = create_app(str(DB_PATH))
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_cookies(client):
    reg = client.post("/api/auth/register", json={"username": "threaduser", "password": "threadpassword123"})
    assert reg.status_code == 201
    login = client.post("/api/auth/login", json={"username": "threaduser", "password": "threadpassword123"})
    assert login.status_code == 200
    return dict(login.cookies)


def test_api_upload_executes_in_worker_thread(client, auth_cookies):
    """Verifies that ingest_upload runs in a background threadpool thread, not the main event loop thread."""
    import app.api.routers.documents as doc_router

    captured_threads = []
    original_ingest = doc_router.ingest_upload

    def _spy_ingest(user_id, original_name, content):
        captured_threads.append(threading.current_thread())
        return original_ingest(user_id, original_name, content)

    main_thread = threading.main_thread()

    with patch.object(doc_router, "ingest_upload", side_effect=_spy_ingest):
        files = {"files": ("test_async.txt", b"Threadpool verification content.", "text/plain")}
        resp = client.post("/api/documents/upload", files=files, cookies=auth_cookies)

    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    assert results[0]["status"] == "ready"

    # Confirms ingest_upload was offloaded to a thread other than the main asyncio thread
    assert len(captured_threads) == 1
    worker_thread = captured_threads[0]
    assert worker_thread != main_thread, "ingest_upload ran synchronously on main thread!"
