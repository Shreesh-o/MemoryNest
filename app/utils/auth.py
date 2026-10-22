"""Authentication helpers (register/login) used by the Streamlit auth gate.

Kept as plain functions so they are trivially unit-testable without Streamlit.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple

from app.database.models import User
from app.database.repositories import UserRepository
from app.utils.security import hash_password, verify_password
from app.utils.validators import validate_email

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9._-]{3,32}$")


def register(
    username: str, password: str, email: Optional[str] = None
) -> Tuple[Optional[User], Optional[str]]:
    """Create a new user. Returns (user, None) on success or (None, error)."""
    username = (username or "").strip()
    if not _USERNAME_RE.match(username):
        return None, "Username must be 3-32 characters: letters, digits, dot, dash, underscore."
    if not password or len(password) < 6:
        return None, "Password must be at least 6 characters."
    repo = UserRepository()
    if repo.get_by_username(username):
        return None, "Username is already taken."
    cleaned_email: Optional[str] = None
    if email is not None:
        trimmed = email.strip()
        if trimmed:
            ok, reason = validate_email(trimmed)
            if not ok:
                return None, reason
            cleaned_email = trimmed.lower()
            if repo.get_by_email(cleaned_email):
                return None, "Email is already taken."

    try:
        user = repo.create(username, hash_password(password), cleaned_email)
        return user, None
    except Exception as e:  # pragma: no cover - defensive
        return None, f"Registration failed: {e}"


def login(username: str, password: str) -> Tuple[Optional[User], Optional[str]]:
    """Verify credentials. Returns (user, None) on success or (None, error)."""
    username = (username or "").strip()
    repo = UserRepository()
    user = repo.get_by_username(username)
    if user is None:
        return None, "Invalid username or password."
    if not verify_password(password or "", user.password_hash):
        return None, "Invalid username or password."
    return user, None
