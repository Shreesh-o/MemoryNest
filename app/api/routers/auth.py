"""Authentication router: register, login, logout, me."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.schemas import UserPublic, RegisterRequest, LoginRequest
from app.api.security import create_token
from app.api.deps import get_current_user
from app.services.auth_service import register, authenticate
from app.utils.config import COOKIE_SECURE


router = APIRouter()


@router.post("/api/auth/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def api_register(req: RegisterRequest) -> UserPublic:
    """Register a new user."""
    try:
        user = register(req.username, req.password, req.email)
    except ValueError as e:
        msg = str(e)
        if "already taken" in msg.lower():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return UserPublic(id=user.id, username=user.username, email=user.email)


@router.post("/api/auth/login", response_model=UserPublic)
def api_login(req: LoginRequest, response: Response) -> UserPublic:
    """Login and set JWT cookie."""
    user = authenticate(req.username, req.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    token = create_token(user.id, user.username)
    response.set_cookie(
        key="mn_session",
        value=token,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        max_age=int(60 * 60 * 24),  # 1 day
    )
    return UserPublic(id=user.id, username=user.username, email=user.email)


@router.post("/api/auth/logout")
def api_logout(response: Response) -> dict:
    """Clear the session cookie."""
    response.delete_cookie(key="mn_session")
    return {"detail": "Logged out"}


@router.get("/api/auth/me", response_model=UserPublic)
def api_me(user=Depends(get_current_user)) -> UserPublic:
    """Return the current user."""
    return UserPublic(id=user.id, username=user.username, email=user.email)