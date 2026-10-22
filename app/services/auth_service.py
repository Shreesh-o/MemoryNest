"""Auth service: user registration and authentication.

No Streamlit imports. Pure business logic for user auth.
"""

from __future__ import annotations

from typing import Optional

from app.database.models import User
from app.database.repositories import UserRepository
from app.utils.security import hash_password, verify_password
from app.utils.validators import validate_email


_USER_RE = __import__("re").compile(r"^[a-zA-Z0-9._-]{3,32}$")


def register(username: str, password: str, email: Optional[str] = None) -> User:
    """Create a new user. Returns the User on success.

    Raises:
        ValueError: if validation fails (empty username, short password, duplicate user)
    """
    username = (username or "").strip()
    if not _USER_RE.match(username):
        raise ValueError("Username must be 3-32 characters: letters, digits, dot, dash, underscore.")
    if not password or len(password) < 6:
        raise ValueError("Password must be at least 6 characters.")

    repo = UserRepository()
    if repo.get_by_username(username):
        raise ValueError("Username is already taken.")

    cleaned_email: Optional[str] = None
    if email is not None:
        trimmed = email.strip()
        if trimmed:
            ok, reason = validate_email(trimmed)
            if not ok:
                raise ValueError(reason)
            cleaned_email = trimmed.lower()
            if repo.get_by_email(cleaned_email):
                raise ValueError("Email is already taken.")

    try:
        user = repo.create(username, hash_password(password), cleaned_email)
        return user
    except Exception as e:
        raise ValueError(f"Registration failed: {e}")


def update_user_email(user_id: int, email: Optional[str]) -> User:
    """Update user email.

    Validates format, normalizes to lowercase, checks for duplicates.
    If email is None or empty/whitespace, clears (unsets) the email.
    """
    repo = UserRepository()
    user = repo.get_by_id(user_id)
    if user is None:
        raise ValueError("User not found.")

    cleaned_email: Optional[str] = None
    if email is not None:
        trimmed = email.strip()
        if trimmed:
            ok, reason = validate_email(trimmed)
            if not ok:
                raise ValueError(reason)
            cleaned_email = trimmed.lower()
            existing = repo.get_by_email(cleaned_email)
            if existing and existing.id != user_id:
                raise ValueError("Email is already taken.")

    updated = repo.update_email(user_id, cleaned_email)
    if updated is None:
        raise ValueError("User not found.")
    return updated


def authenticate(username: str, password: str) -> User | None:
    """Verify credentials. Returns User on success, None on failure."""
    username = (username or "").strip()
    repo = UserRepository()
    user = repo.get_by_username(username)
    if user is None:
        return None
    if not verify_password(password or "", user.password_hash):
        return None
    return user