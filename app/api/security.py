"""JWT security helpers for the FastAPI layer."""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt

from app.utils.config import JWT_SECRET, JWT_EXPIRE_MINUTES

logger = logging.getLogger(__name__)

# Initialize JWT secret: use env value, or generate a random one and warn
_jwt_secret: Optional[str] = None


def get_jwt_secret() -> str:
    """Return the JWT secret, generating a random one if unset."""
    global _jwt_secret
    if _jwt_secret is not None:
        return _jwt_secret
    secret = JWT_SECRET
    if not secret:
        secret = secrets.token_urlsafe(32)
        logger.warning(
            "JWT_SECRET is not set; generated a random secret. "
            "Tokens will be invalidated on restart. Set JWT_SECRET for production."
        )
    _jwt_secret = secret
    return secret


def create_token(user_id: int, username: str) -> str:
    """Create a JWT token for the given user."""
    secret = get_jwt_secret()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "username": username,
        "iat": now,
        "exp": now + timedelta(minutes=JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_token(token: str) -> dict:
    """Decode and verify a JWT token. Returns the payload or raises."""
    secret = get_jwt_secret()
    return jwt.decode(token, secret, algorithms=["HS256"])