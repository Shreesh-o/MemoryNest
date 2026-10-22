"""Tests for Google OAuth connection, token encryption, state validation, and Calendar client."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
import jwt
from google.auth.exceptions import RefreshError

from app.api.main import create_app
from app.api.security import get_jwt_secret
from app.database.repositories import GoogleConnectionRepository, UserRepository
from app.services.google_auth_service import (
    create_oauth_state,
    disconnect_google,
    get_calendar_client,
    get_google_status,
    handle_callback,
    is_google_configured,
    verify_oauth_state,
)
from app.utils import config
from app.utils.security import decrypt_token, encrypt_token


@pytest.fixture()
def client(tmp_path):
    import app.utils.config as config_module
    db_path = str(config_module.DB_PATH)
    app = create_app(db_path)
    with TestClient(app) as test_client:
        yield test_client


def _register_and_login(client: TestClient, username: str, password: str = "password123") -> tuple[dict, int]:
    resp = client.post("/api/auth/register", json={"username": username, "password": password})
    assert resp.status_code == 201
    resp = client.post("/api/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200
    user = UserRepository().get_by_username(username)
    assert user is not None
    return dict(resp.cookies), user.id


def test_token_encryption_roundtrip(monkeypatch):
    """Tokens are encrypted and decrypted correctly with both default secret and custom key."""
    # 1. Roundtrip with default secret
    token = "1//04fake_refresh_token_abc_xyz_12345"
    encrypted = encrypt_token(token)
    assert encrypted != token
    assert token not in encrypted
    decrypted = decrypt_token(encrypted)
    assert decrypted == token

    # 2. Roundtrip with custom TOKEN_ENCRYPTION_KEY
    monkeypatch.setattr(config, "TOKEN_ENCRYPTION_KEY", "super-secret-encryption-passphrase-32b")
    encrypted_custom = encrypt_token(token)
    assert encrypted_custom != token
    assert decrypt_token(encrypted_custom) == token

    # 3. Empty string
    assert encrypt_token("") == ""
    assert decrypt_token("") == ""


def test_oauth_state_validation():
    """State JWT contains user_id, rejects tampered or expired tokens, and enforces purpose."""
    user_id = 42
    state = create_oauth_state(user_id)
    assert verify_oauth_state(state) == user_id

    # Tampered state
    tampered_state = state[:-5] + "XXXXX"
    with pytest.raises(ValueError, match="Invalid OAuth state"):
        verify_oauth_state(tampered_state)

    # Expired state
    secret = get_jwt_secret()
    past = datetime.now(timezone.utc) - timedelta(minutes=20)
    expired_payload = {
        "sub": str(user_id),
        "purpose": "google_oauth_state",
        "iat": past - timedelta(minutes=5),
        "exp": past,
    }
    expired_state = jwt.encode(expired_payload, secret, algorithm="HS256")
    with pytest.raises(ValueError, match="OAuth state has expired"):
        verify_oauth_state(expired_state)

    # Wrong purpose
    wrong_purpose_payload = {
        "sub": str(user_id),
        "purpose": "login_session",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
    }
    wrong_purpose_state = jwt.encode(wrong_purpose_payload, secret, algorithm="HS256")
    with pytest.raises(ValueError, match="Invalid OAuth state purpose"):
        verify_oauth_state(wrong_purpose_state)


def test_not_configured_behavior(client, monkeypatch):
    """When GOOGLE_CLIENT_ID / SECRET are not set, endpoints return not-configured status safely."""
    monkeypatch.setattr(config, "GOOGLE_CLIENT_ID", "")
    monkeypatch.setattr(config, "GOOGLE_CLIENT_SECRET", "")

    cookies, user_id = _register_and_login(client, "unconfigured_user")

    # 1. Status endpoint
    resp = client.get("/api/google/status", cookies=cookies)
    assert resp.status_code == 200
    assert resp.json() == {"configured": False, "connected": False, "google_email": None}

    # 2. Connect endpoint returns 400
    resp = client.post("/api/google/connect", cookies=cookies)
    assert resp.status_code == 400
    assert "not configured" in resp.json()["detail"]

    # 3. Callback redirects to ?google=error
    resp = client.get("/api/google/callback?code=foo&state=bar", follow_redirects=False)
    assert resp.status_code == 303
    assert "/reminders?google=error" in resp.headers["location"]

    # 4. get_calendar_client returns None
    assert get_calendar_client(user_id) is None


def test_connect_and_callback_flow(client, monkeypatch):
    """Successful OAuth connect and callback exchange stores encrypted refresh token."""
    monkeypatch.setattr(config, "GOOGLE_CLIENT_ID", "mock-client-id.apps.googleusercontent.com")
    monkeypatch.setattr(config, "GOOGLE_CLIENT_SECRET", "mock-client-secret")

    cookies, user_id = _register_and_login(client, "oauth_user")

    # 1. Connect endpoint returns auth_url
    resp = client.post("/api/google/connect", cookies=cookies)
    assert resp.status_code == 200
    auth_url = resp.json()["auth_url"]
    assert "accounts.google.com" in auth_url
    assert "mock-client-id" in auth_url
    assert "calendar.events" in auth_url

    # 2. Mock Flow token exchange
    state = create_oauth_state(user_id)
    mock_creds = MagicMock()
    mock_creds.refresh_token = "1//mock-refresh-token-987"
    mock_creds.id_token = {"email": "oauth_user@gmail.com"}
    mock_creds.scopes = ["https://www.googleapis.com/auth/calendar.events"]

    with patch("app.services.google_auth_service._build_flow") as mock_build_flow:
        mock_flow = MagicMock()
        mock_flow.credentials = mock_creds
        mock_build_flow.return_value = mock_flow

        callback_resp = client.get(f"/api/google/callback?code=mock_auth_code&state={state}", follow_redirects=False)
        assert callback_resp.status_code == 303
        assert "/reminders?google=connected" in callback_resp.headers["location"]
        mock_flow.fetch_token.assert_called_once_with(code="mock_auth_code")

    # 3. Verify DB row and status endpoint
    repo = GoogleConnectionRepository()
    conn = repo.get_by_user_id(user_id)
    assert conn is not None
    assert conn.google_email == "oauth_user@gmail.com"
    assert conn.refresh_token_encrypted != "1//mock-refresh-token-987"
    assert decrypt_token(conn.refresh_token_encrypted) == "1//mock-refresh-token-987"

    status_resp = client.get("/api/google/status", cookies=cookies)
    assert status_resp.status_code == 200
    assert status_resp.json() == {
        "configured": True,
        "connected": True,
        "google_email": "oauth_user@gmail.com",
    }


def test_callback_error_and_invalid_state(client, monkeypatch):
    """Callback with error param, missing state, or tampered state redirects to google=error."""
    monkeypatch.setattr(config, "GOOGLE_CLIENT_ID", "mock-client-id")
    monkeypatch.setattr(config, "GOOGLE_CLIENT_SECRET", "mock-client-secret")

    # Error param
    resp = client.get("/api/google/callback?error=access_denied", follow_redirects=False)
    assert resp.status_code == 303
    assert "/reminders?google=error" in resp.headers["location"]

    # Missing state
    resp = client.get("/api/google/callback?code=123", follow_redirects=False)
    assert resp.status_code == 303
    assert "/reminders?google=error" in resp.headers["location"]

    # Tampered state
    resp = client.get("/api/google/callback?code=123&state=badstate", follow_redirects=False)
    assert resp.status_code == 303
    assert "/reminders?google=error" in resp.headers["location"]


def test_user_isolation(client, monkeypatch):
    """One user's Google connection is strictly isolated from other users."""
    monkeypatch.setattr(config, "GOOGLE_CLIENT_ID", "mock-client-id")
    monkeypatch.setattr(config, "GOOGLE_CLIENT_SECRET", "mock-client-secret")

    cookies_a, user_a_id = _register_and_login(client, "alice")
    cookies_b, user_b_id = _register_and_login(client, "bob")

    # Alice connects
    repo = GoogleConnectionRepository()
    repo.upsert(
        user_id=user_a_id,
        google_email="alice@gmail.com",
        refresh_token_encrypted=encrypt_token("alice-token"),
        scope="https://www.googleapis.com/auth/calendar.events",
    )

    # Bob's status must show not connected
    status_b = client.get("/api/google/status", cookies=cookies_b)
    assert status_b.status_code == 200
    assert status_b.json() == {"configured": True, "connected": False, "google_email": None}

    # Bob disconnecting does not affect Alice
    client.post("/api/google/disconnect", cookies=cookies_b)
    assert repo.get_by_user_id(user_a_id) is not None
    assert repo.get_by_user_id(user_b_id) is None

    # Alice status shows connected
    status_a = client.get("/api/google/status", cookies=cookies_a)
    assert status_a.status_code == 200
    assert status_a.json() == {"configured": True, "connected": True, "google_email": "alice@gmail.com"}


def test_disconnect_google(client, monkeypatch):
    """Disconnecting revokes the token with Google (best effort) and deletes the connection row."""
    monkeypatch.setattr(config, "GOOGLE_CLIENT_ID", "mock-client-id")
    monkeypatch.setattr(config, "GOOGLE_CLIENT_SECRET", "mock-client-secret")

    cookies, user_id = _register_and_login(client, "disconnect_user")
    repo = GoogleConnectionRepository()
    repo.upsert(
        user_id=user_id,
        google_email="disconnect@gmail.com",
        refresh_token_encrypted=encrypt_token("token-to-revoke"),
        scope="https://www.googleapis.com/auth/calendar.events",
    )

    with patch("requests.post") as mock_revoke:
        mock_revoke.return_value = MagicMock(status_code=200)
        resp = client.post("/api/google/disconnect", cookies=cookies)
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok", "disconnected": True}

        mock_revoke.assert_called_once()
        assert "oauth2.googleapis.com/revoke" in mock_revoke.call_args[0][0]
        assert mock_revoke.call_args[1]["params"]["token"] == "token-to-revoke"

    # Row is deleted
    assert repo.get_by_user_id(user_id) is None
    status = client.get("/api/google/status", cookies=cookies)
    assert status.json()["connected"] is False


def test_get_calendar_client_revoked_token(monkeypatch):
    """When a refresh token is revoked/expired, get_calendar_client marks the user disconnected."""
    monkeypatch.setattr(config, "GOOGLE_CLIENT_ID", "mock-client-id")
    monkeypatch.setattr(config, "GOOGLE_CLIENT_SECRET", "mock-client-secret")

    user_repo = UserRepository()
    user = user_repo.create("revoked_user", "hashed", "revoked@example.com")

    conn_repo = GoogleConnectionRepository()
    conn_repo.upsert(
        user_id=user.id,
        google_email="revoked@gmail.com",
        refresh_token_encrypted=encrypt_token("revoked-token"),
        scope="https://www.googleapis.com/auth/calendar.events",
    )

    with patch("google.oauth2.credentials.Credentials.refresh") as mock_refresh:
        mock_refresh.side_effect = RefreshError("invalid_grant: Token has been expired or revoked.")

        client = get_calendar_client(user.id)
        assert client is None

    # Verify user connection row was deleted
    assert conn_repo.get_by_user_id(user.id) is None


def test_get_calendar_client_success(monkeypatch):
    """When credentials refresh succeeds, an authorized Calendar service is returned."""
    monkeypatch.setattr(config, "GOOGLE_CLIENT_ID", "mock-client-id")
    monkeypatch.setattr(config, "GOOGLE_CLIENT_SECRET", "mock-client-secret")

    user_repo = UserRepository()
    user = user_repo.create("active_user", "hashed", "active@example.com")

    conn_repo = GoogleConnectionRepository()
    conn_repo.upsert(
        user_id=user.id,
        google_email="active@gmail.com",
        refresh_token_encrypted=encrypt_token("active-token"),
        scope="https://www.googleapis.com/auth/calendar.events",
    )

    mock_service = MagicMock()
    with patch("google.oauth2.credentials.Credentials.refresh"), \
         patch("app.services.google_auth_service.build", return_value=mock_service) as mock_build:
        service = get_calendar_client(user.id)
        assert service == mock_service
        mock_build.assert_called_once()
        assert mock_build.call_args[0] == ("calendar", "v3")
