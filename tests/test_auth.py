"""Tests for auth (register/login) and password hashing."""

from __future__ import annotations

import pytest

from app.utils.auth import login, register
from app.utils.security import hash_password, verify_password


@pytest.fixture()
def db(tmp_path, monkeypatch):
    from app.database.database import init_db

    db_path = tmp_path / "auth.db"
    init_db(db_path)
    monkeypatch.setattr("app.database.database.DB_PATH", db_path)
    yield db_path
    db_path.unlink(missing_ok=True)


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
