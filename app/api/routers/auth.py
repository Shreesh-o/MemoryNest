"""Authentication router: register, login, logout, me."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status, Body

from app.api.schemas import (
    UserPublic,
    RegisterRequest,
    LoginRequest,
    UpdateEmailRequest,
    UpdateProfileRequest,
    ChangePasswordRequest,
    DeactivateAccountRequest,
)
from app.api.security import create_token
from app.api.deps import get_current_user
from app.services.auth_service import (
    register,
    authenticate,
    update_user_email,
    update_profile,
    change_password,
    deactivate_user,
)
from app.utils.config import COOKIE_SECURE, JWT_EXPIRE_MINUTES


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
        max_age=int(JWT_EXPIRE_MINUTES * 60),
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


@router.patch("/api/auth/me/email", response_model=UserPublic)
def api_update_email(req: UpdateEmailRequest, user=Depends(get_current_user)) -> UserPublic:
    """Update the current user's email."""
    try:
        updated = update_user_email(user.id, req.email)
    except ValueError as e:
        msg = str(e)
        if "already taken" in msg.lower():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return UserPublic(id=updated.id, username=updated.username, email=updated.email)


@router.patch("/api/auth/me/profile", response_model=UserPublic)
def api_update_profile(
    req: UpdateProfileRequest,
    response: Response,
    user=Depends(get_current_user),
) -> UserPublic:
    """Update user username and/or email."""
    try:
        updated = update_profile(user.id, username=req.username, email=req.email)
    except ValueError as e:
        msg = str(e)
        if "already taken" in msg.lower():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    # If username changed, issue a refreshed token so user session remains valid
    if updated.username != user.username:
        token = create_token(updated.id, updated.username)
        response.set_cookie(
            key="mn_session",
            value=token,
            httponly=True,
            samesite="lax",
            secure=COOKIE_SECURE,
            max_age=int(JWT_EXPIRE_MINUTES * 60),
        )

    return UserPublic(id=updated.id, username=updated.username, email=updated.email)


@router.post("/api/auth/me/password")
def api_change_password(
    req: ChangePasswordRequest,
    user=Depends(get_current_user),
) -> dict:
    """Change user password."""
    try:
        change_password(user.id, req.current_password, req.new_password)
    except ValueError as e:
        msg = str(e)
        if "incorrect" in msg.lower():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return {"detail": "Password updated successfully"}


@router.post("/api/auth/me/deactivate")
def api_deactivate_account(
    response: Response,
    req: DeactivateAccountRequest = Body(default_factory=DeactivateAccountRequest),
    user=Depends(get_current_user),
) -> dict:
    """Deactivate (delete) user account, cleaning up all documents, vectors, and session."""
    try:
        deactivate_user(user.id, req.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    response.delete_cookie(key="mn_session")
    return {"detail": "Account deactivated successfully"}


@router.delete("/api/auth/me")
def api_deactivate_account_delete(
    response: Response,
    user=Depends(get_current_user),
) -> dict:
    """Deactivate (delete) user account via DELETE."""
    deactivate_user(user.id, None)
    response.delete_cookie(key="mn_session")
    return {"detail": "Account deactivated successfully"}
