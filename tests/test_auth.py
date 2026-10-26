"""Tests for auth (register/login) and password hashing."""

from __future__ import annotations

import pytest

from app.utils.auth import login, register
from app.utils.security import hash_password, verify_password


@pytest.fixture()
def db():
    """Fresh per-test DB, set up by the autouse test_storage fixture in conftest.py."""
    import app.utils.config as config_module
    return config_module.DB_PATH


def test_hash_roundtrip():
    h = hash_password("hunter2")
    assert verify_password("hunter2", h)
    assert not verify_password("hunter3", h)
    assert h != hash_password("hunter2")  # salted


def test_register_and_login(db):
    user, err = register("alice", "secret123", "alice@example.com")
    assert user and user.username == "alice" and err is None
    assert "alice@example.com" == user.email

    logged, err = login("alice", "secret123")
    assert logged and logged.id == user.id and err is None
    assert not verify_password("wrong", logged.password_hash)


def test_register_rejects_bad_username(db):
    _, err = register("ab", "secret123")
    assert "3-32" in err
    _, err = register("bad name!", "secret123")
    assert err is not None


def test_register_rejects_short_password(db):
    _, err = register("bob", "123")
    assert "6 characters" in err


def test_register_rejects_duplicate(db):
    register("carol", "secret123")
    _, err = register("carol", "other123")
    assert "taken" in err


def test_login_wrong_password(db):
    register("dave", "secret123")
    user, err = login("dave", "nope")
    assert user is None and err is not None


def test_login_unknown_user(db):
    user, err = login("ghost", "secret123")
    assert user is None and "Invalid" in err


def test_register_rejects_invalid_email(db):
    _, err = register("validuser", "secret123", "not-an-email")
    assert err is not None
    assert "email" in err.lower()


def test_register_rejects_duplicate_email(db):
    user, err = register("user1", "secret123", "shared@example.com")
    assert user is not None and err is None
    _, err2 = register("user2", "secret123", "shared@example.com")
    assert "taken" in err2.lower()


def test_update_user_email_service(db):
    from app.services.auth_service import register as service_register, update_user_email
    user = service_register("serviceuser", "secret123")
    assert user.email is None

    # Set valid email with mixed case -> normalized
    updated = update_user_email(user.id, "ServiceUser@Example.COM")
    assert updated.email == "serviceuser@example.com"

    # Unset email with None
    updated = update_user_email(user.id, None)
    assert updated.email is None

    # Set valid email again
    updated = update_user_email(user.id, "new@example.com")
    assert updated.email == "new@example.com"

    # Unset email with empty string
    updated = update_user_email(user.id, "")
    assert updated.email is None

    # Invalid email raises ValueError
    with pytest.raises(ValueError, match="email"):
        update_user_email(user.id, "invalid-email")


def test_jwt_missing_or_invalid_sub_returns_401():
    import jwt
    from fastapi.testclient import TestClient
    from app.api.main import create_app
    from app.api.security import get_jwt_secret

    client = TestClient(create_app())
    secret = get_jwt_secret()

    # 1. Missing sub
    token_no_sub = jwt.encode({"username": "nosub"}, secret, algorithm="HS256")
    resp = client.get("/api/auth/me", cookies={"mn_session": token_no_sub})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid token"

    # 2. Non-numeric sub
    token_str_sub = jwt.encode({"sub": "not-an-int", "username": "bad"}, secret, algorithm="HS256")
    resp = client.get("/api/auth/me", cookies={"mn_session": token_str_sub})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid token"

    # 3. None/empty sub
    token_empty_sub = jwt.encode({"sub": "", "username": "bad"}, secret, algorithm="HS256")
    resp = client.get("/api/auth/me", cookies={"mn_session": token_empty_sub})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid token"


