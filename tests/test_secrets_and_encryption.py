"""Regression tests for ARC-04: Persistent and safe authentication and encryption secrets."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from cryptography.fernet import InvalidToken

from app.api.security import (
    create_token,
    decode_token,
    get_jwt_secret,
    reset_jwt_secret,
)
from app.database.repositories import GoogleConnectionRepository, UserRepository
from app.services.google_auth_service import get_calendar_client
from app.utils.security import decrypt_token, encrypt_token, get_encryption_fernet


def test_production_rejects_missing_jwt_secret(monkeypatch):
    """Production mode must raise RuntimeError if JWT_SECRET is unset."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET", "")
    monkeypatch.setattr("app.utils.config.JWT_SECRET", "")
    reset_jwt_secret()

    with pytest.raises(RuntimeError, match="Production requires JWT_SECRET"):
        get_jwt_secret()


def test_production_rejects_placeholder_jwt_secret(monkeypatch):
    """Production mode must raise RuntimeError if JWT_SECRET is a known placeholder."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET", "some_super_long_random_secret_string_here")
    reset_jwt_secret()

    with pytest.raises(RuntimeError, match="cannot use a known placeholder"):
        get_jwt_secret()


def test_production_rejects_missing_token_encryption_key(monkeypatch):
    """Production mode must raise RuntimeError if TOKEN_ENCRYPTION_KEY is unset."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET", "a" * 40)
    monkeypatch.delenv("TOKEN_ENCRYPTION_KEY", raising=False)
    reset_jwt_secret()

    with pytest.raises(RuntimeError, match="Production requires TOKEN_ENCRYPTION_KEY"):
        get_encryption_fernet()


def test_production_accepts_strong_secrets(monkeypatch):
    """Production mode succeeds with properly configured, non-placeholder secrets."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET", "strong_production_jwt_secret_with_sufficient_entropy_123")
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", "strong_token_encryption_key_456789")
    reset_jwt_secret()

    assert get_jwt_secret() == "strong_production_jwt_secret_with_sufficient_entropy_123"
    token = encrypt_token("sample_refresh_token")
    assert decrypt_token(token) == "sample_refresh_token"


def test_development_persists_generated_secret(tmp_path, monkeypatch):
    """In development, an unset JWT_SECRET persists to .jwt_secret across simulated restarts."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("JWT_SECRET", "")
    monkeypatch.setattr("app.utils.config.JWT_SECRET", "")

    fake_project_root = tmp_path / "project"
    fake_project_root.mkdir()
    monkeypatch.setattr("app.api.security.PROJECT_ROOT", fake_project_root)
    monkeypatch.setattr("app.utils.config.PROJECT_ROOT", fake_project_root)
    reset_jwt_secret()

    # First startup: generates secret and saves to .jwt_secret
    secret1 = get_jwt_secret()
    secret_file = fake_project_root / ".jwt_secret"
    assert secret_file.exists()
    assert secret_file.read_text().strip() == secret1

    token = create_token(user_id=42, username="alice")

    # Simulate process restart
    reset_jwt_secret()
    secret2 = get_jwt_secret()
    assert secret1 == secret2

    # Previously issued token decodes successfully after restart
    payload = decode_token(token)
    assert payload["sub"] == "42"
    assert payload["username"] == "alice"


def test_token_encryption_legacy_key_fallback(monkeypatch):
    """Setting TOKEN_ENCRYPTION_KEY preserves decryptability of tokens encrypted with the legacy JWT secret."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    legacy_jwt_secret = "legacy_jwt_secret_key_used_before_token_key_was_set"
    monkeypatch.setenv("JWT_SECRET", legacy_jwt_secret)
    monkeypatch.delenv("TOKEN_ENCRYPTION_KEY", raising=False)
    reset_jwt_secret()

    # Token encrypted when only JWT_SECRET was configured
    original_plain = "google_refresh_token_xyz_123"
    cipher_text = encrypt_token(original_plain)

    # Now the user configures a dedicated TOKEN_ENCRYPTION_KEY
    new_encryption_key = "brand_new_dedicated_token_encryption_key_789"
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", new_encryption_key)
    reset_jwt_secret()

    # Decrypt must transparently succeed using fallback key
    decrypted = decrypt_token(cipher_text)
    assert decrypted == original_plain


def test_decryption_failure_preserves_database_record(monkeypatch):
    """Decryption failure must log an error and return None without deleting the Google connection record."""
    user_repo = UserRepository()
    user = user_repo.create("google_user", "pw_hash", "guser@example.com")

    conn_repo = GoogleConnectionRepository()
    # Save a connection with invalid / corrupted ciphertext
    conn_repo.upsert(
        user_id=user.id,
        google_email="guser@example.com",
        refresh_token_encrypted="garbage_unparseable_encrypted_token",
        scope="calendar",
    )

    # Mock is_google_configured to return True so get_calendar_client attempts decryption
    monkeypatch.setattr("app.services.google_auth_service.is_google_configured", lambda: True)

    client = get_calendar_client(user.id)
    assert client is None

    # CRITICAL: Connection record must still exist in the database!
    record = conn_repo.get_by_user_id(user.id)
    assert record is not None
    assert record.google_email == "guser@example.com"
