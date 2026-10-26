"""Password hashing and token encryption helpers."""

from __future__ import annotations

import base64
import hashlib
import logging
import os
from typing import Optional

import bcrypt
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def get_encryption_fernet(key: Optional[str] = None) -> Fernet:
    """Return a Fernet cipher instance using TOKEN_ENCRYPTION_KEY or derived from JWT secret.

    If key is explicitly provided, derives Fernet cipher from it.
    Otherwise:
    - In production: Requires a strong, non-placeholder TOKEN_ENCRYPTION_KEY.
    - In development/test: Prefers TOKEN_ENCRYPTION_KEY, falling back to persistent JWT secret.
    """
    from app.api.security import KNOWN_PLACEHOLDER_SECRETS, get_jwt_secret, is_production
    from app.utils import config

    if key is not None:
        key_str = key
    else:
        configured_key = os.environ.get("TOKEN_ENCRYPTION_KEY") if "TOKEN_ENCRYPTION_KEY" in os.environ else getattr(config, "TOKEN_ENCRYPTION_KEY", "")
        prod = is_production()
        if prod:
            if not configured_key:
                raise RuntimeError(
                    "Production requires TOKEN_ENCRYPTION_KEY to be explicitly configured. "
                    "Set TOKEN_ENCRYPTION_KEY in environment or .env."
                )
            if configured_key.lower() in KNOWN_PLACEHOLDER_SECRETS or len(configured_key) < 16:
                raise RuntimeError(
                    "Production cannot use a known placeholder or weak TOKEN_ENCRYPTION_KEY "
                    "(must be >= 16 characters and non-placeholder)."
                )
            key_str = configured_key
        else:
            if configured_key:
                key_str = configured_key
            else:
                key_str = get_jwt_secret()

    derived = base64.urlsafe_b64encode(hashlib.sha256(key_str.encode("utf-8")).digest())
    return Fernet(derived)


def encrypt_token(plain_token: str) -> str:
    """Encrypt a plain string token (e.g. OAuth refresh token) with Fernet."""
    if not plain_token:
        return ""
    fernet = get_encryption_fernet()
    return fernet.encrypt(plain_token.encode("utf-8")).decode("utf-8")


def decrypt_token(cipher_token: str) -> str:
    """Decrypt a Fernet-encrypted token with automatic fallback for key compatibility.

    Attempts decryption with the primary key first.
    If decryption fails and a secondary key is available (e.g. legacy JWT secret
    when a dedicated TOKEN_ENCRYPTION_KEY is configured), tries the fallback
    to prevent invalidating existing encrypted records.
    """
    if not cipher_token:
        return ""

    from app.api.security import get_jwt_secret
    from app.utils import config

    # 1. Try primary encryption key
    primary_fernet = get_encryption_fernet()
    try:
        return primary_fernet.decrypt(cipher_token.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        pass

    # 2. Try fallback key if TOKEN_ENCRYPTION_KEY and JWT_SECRET differ
    configured_key = os.environ.get("TOKEN_ENCRYPTION_KEY") if "TOKEN_ENCRYPTION_KEY" in os.environ else getattr(config, "TOKEN_ENCRYPTION_KEY", "")
    try:
        jwt_sec = get_jwt_secret()
    except Exception:
        jwt_sec = None

    if configured_key and jwt_sec and configured_key != jwt_sec:
        try:
            fallback_fernet = get_encryption_fernet(key=jwt_sec)
            return fallback_fernet.decrypt(cipher_token.encode("utf-8")).decode("utf-8")
        except InvalidToken:
            pass

    raise InvalidToken("Token decryption failed with all available keys.")

