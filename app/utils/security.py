"""Password hashing and token encryption helpers."""

from __future__ import annotations

import base64
import hashlib

import bcrypt
from cryptography.fernet import Fernet


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def get_encryption_fernet() -> Fernet:
    """Return a Fernet cipher instance using TOKEN_ENCRYPTION_KEY or derived from JWT secret."""
    from app.api.security import get_jwt_secret
    from app.utils import config

    key_str = config.TOKEN_ENCRYPTION_KEY or get_jwt_secret()
    derived = base64.urlsafe_b64encode(hashlib.sha256(key_str.encode("utf-8")).digest())
    return Fernet(derived)


def encrypt_token(plain_token: str) -> str:
    """Encrypt a plain string token (e.g. OAuth refresh token) with Fernet."""
    if not plain_token:
        return ""
    fernet = get_encryption_fernet()
    return fernet.encrypt(plain_token.encode("utf-8")).decode("utf-8")


def decrypt_token(cipher_token: str) -> str:
    """Decrypt a Fernet-encrypted token."""
    if not cipher_token:
        return ""
    fernet = get_encryption_fernet()
    return fernet.decrypt(cipher_token.encode("utf-8")).decode("utf-8")

