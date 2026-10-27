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


def update_profile(
    user_id: int,
    username: Optional[str] = None,
    email: Optional[str] = None,
) -> User:
    """Update user username and/or email."""
    repo = UserRepository()
    user = repo.get_by_id(user_id)
    if user is None:
        raise ValueError("User not found.")

    cleaned_username: Optional[str] = None
    if username is not None:
        trimmed_u = username.strip()
        if trimmed_u and trimmed_u != user.username:
            if not _USER_RE.match(trimmed_u):
                raise ValueError("Username must be 3-32 characters: letters, digits, dot, dash, underscore.")
            existing_u = repo.get_by_username(trimmed_u)
            if existing_u and existing_u.id != user_id:
                raise ValueError("Username is already taken.")
            cleaned_username = trimmed_u

    cleaned_email: Optional[str] = None
    email_changed = False
    if email is not None:
        trimmed_e = email.strip()
        if trimmed_e:
            ok, reason = validate_email(trimmed_e)
            if not ok:
                raise ValueError(reason)
            cleaned_email = trimmed_e.lower()
            if cleaned_email != (user.email or "").lower():
                existing_e = repo.get_by_email(cleaned_email)
                if existing_e and existing_e.id != user_id:
                    raise ValueError("Email is already taken.")
                email_changed = True
        else:
            if user.email is not None:
                cleaned_email = None
                email_changed = True

    updated = repo.update_profile(
        user_id,
        username=cleaned_username,
        email=cleaned_email,
        update_email_flag=email_changed,
    )
    if updated is None:
        raise ValueError("User not found.")
    return updated


def change_password(user_id: int, current_password: str, new_password: str) -> bool:
    """Verify current password and update to new password."""
    repo = UserRepository()
    user = repo.get_by_id(user_id)
    if user is None:
        raise ValueError("User not found.")
    if not verify_password(current_password or "", user.password_hash):
        raise ValueError("Current password is incorrect.")
    if not new_password or len(new_password) < 6:
        raise ValueError("New password must be at least 6 characters.")
    repo.update_password(user_id, hash_password(new_password))
    return True


def deactivate_user(user_id: int, password: Optional[str] = None) -> bool:
    """Deactivate (delete) user account and clean up all their documents/data."""
    repo = UserRepository()
    user = repo.get_by_id(user_id)
    if user is None:
        raise ValueError("User not found.")

    if password is not None and password != "":
        if not verify_password(password, user.password_hash):
            raise ValueError("Incorrect password.")

    # Clean up all user's documents (ChromaDB vectors, cache, files on disk)
    try:
        from app.database.repositories import DocumentRepository
        from app.services.document_service import delete_document
        doc_repo = DocumentRepository()
        user_docs = doc_repo.list_by_user(user_id)
        for doc in user_docs:
            try:
                delete_document(user_id, doc.id)
            except Exception:
                pass
    except Exception:
        pass

    repo.delete(user_id)
    return True