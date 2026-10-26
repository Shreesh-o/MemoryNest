"""JWT security helpers for the FastAPI layer."""

from __future__ import annotations

import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import jwt

from app.utils.config import JWT_EXPIRE_MINUTES, PROJECT_ROOT

logger = logging.getLogger(__name__)

# Known placeholders that must never be used in production
KNOWN_PLACEHOLDER_SECRETS = {
    "some_super_long_random_secret_string_here",
    "your-secret-key",
    "change-me",
    "secret",
    "changeme",
    "placeholder",
}

# In-memory cached JWT secret
_jwt_secret: Optional[str] = None


def is_production() -> bool:
    """Check whether the application is running in production mode."""
    env = os.environ.get("ENVIRONMENT", os.environ.get("APP_ENV", "")).lower()
    return env in ("production", "prod")


def reset_jwt_secret() -> None:
    """Reset cached JWT secret in memory (primarily for testing)."""
    global _jwt_secret
    _jwt_secret = None


def get_jwt_secret() -> str:
    """Return the JWT secret.

    Policy:
    - In production: Requires a strong, explicitly configured JWT_SECRET (not empty,
      not a known placeholder, and >= 32 chars). Raises RuntimeError otherwise.
    - In development / test: Uses JWT_SECRET if provided (warns if a placeholder).
      If unset, loads from persistent PROJECT_ROOT/.jwt_secret (or generates it once
      with 0600 permissions) so tokens remain valid across process restarts.
    """
    global _jwt_secret
    if _jwt_secret is not None:
        return _jwt_secret

    from app.utils import config

    configured = os.environ.get("JWT_SECRET") if "JWT_SECRET" in os.environ else getattr(config, "JWT_SECRET", "")
    prod = is_production()

    if prod:
        if not configured:
            raise RuntimeError(
                "Production requires JWT_SECRET to be explicitly configured. "
                "Set JWT_SECRET in environment or .env."
            )
        if configured.lower() in KNOWN_PLACEHOLDER_SECRETS or len(configured) < 32:
            raise RuntimeError(
                "Production cannot use a known placeholder or weak JWT_SECRET "
                "(must be >= 32 characters and non-placeholder)."
            )
        _jwt_secret = configured
        return _jwt_secret

    # Development / test mode:
    if configured:
        if configured.lower() in KNOWN_PLACEHOLDER_SECRETS:
            logger.warning(
                "Using placeholder JWT_SECRET in development/test. "
                "Do NOT use this placeholder in production."
            )
        _jwt_secret = configured
        return _jwt_secret

    # Check for persistent .jwt_secret file
    secret_file = PROJECT_ROOT / ".jwt_secret"
    if secret_file.exists():
        try:
            saved = secret_file.read_text(encoding="utf-8").strip()
            if saved and len(saved) >= 32:
                _jwt_secret = saved
                return _jwt_secret
        except Exception as e:
            logger.warning("Failed to read %s: %s", secret_file, e)

    # Generate persistent development secret
    new_secret = secrets.token_hex(32)
    try:
        secret_file.write_text(new_secret, encoding="utf-8")
        secret_file.chmod(0o600)
        logger.info("Generated persistent development JWT secret at %s", secret_file)
    except Exception as e:
        logger.warning("Failed to write persistent secret to %s: %s", secret_file, e)

    _jwt_secret = new_secret
    return _jwt_secret


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