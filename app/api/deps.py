"""FastAPI dependencies."""

from __future__ import annotations

from typing import Optional

from fastapi import HTTPException, Request, status

from app.api.security import decode_token
from app.database.models import User


def _extract_token(request: Request) -> Optional[str]:
    """Extract JWT token from cookie or Authorization header."""
    # First check cookie
    token = request.cookies.get("mn_session")
    if token:
        return token
    # Then check Authorization header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    return None


def get_current_user(request: Request) -> User:
    """Extract and verify JWT token, return the authenticated user."""
    token = _extract_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = int(payload.get("sub"))
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    from app.database.repositories import UserRepository
    user = UserRepository().get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user