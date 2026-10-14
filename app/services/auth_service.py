"""Auth service: user registration and authentication.

No Streamlit imports. Pure business logic for user auth.
"""

from __future__ import annotations

from typing import Optional

from app.database.models import User
from app.database.repositories import UserRepository
from app.utils.security import hash_password, verify_password


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

    try:
        user = repo.create(username, hash_password(password), email)
        return user
    except Exception as e:
        raise ValueError(f"Registration failed: {e}")


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