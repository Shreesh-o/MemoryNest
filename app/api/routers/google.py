"""Google OAuth and Calendar API router."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse

from app.api.deps import get_current_user
from app.api.schemas import (
    GoogleConnectResponse,
    GoogleDisconnectResponse,
    GoogleStatusResponse,
)
from app.database.models import User
from app.services.google_auth_service import (
    disconnect_google,
    generate_connect_url,
    get_google_status,
    handle_callback,
    is_google_configured,
)
from app.utils import config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/google", tags=["google"])


@router.get("/status", response_model=GoogleStatusResponse)
def get_status(current_user: User = Depends(get_current_user)) -> GoogleStatusResponse:
    """Check if Google integration is configured and if the current user is connected."""
    status_data = get_google_status(current_user.id)
    return GoogleStatusResponse(**status_data)


@router.post("/connect", response_model=GoogleConnectResponse)
def connect(current_user: User = Depends(get_current_user)) -> GoogleConnectResponse:
    """Generate authorization URL to start Google OAuth connect flow."""
    if not is_google_configured():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google integration is not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
        )
    try:
        auth_url = generate_connect_url(current_user.id)
        return GoogleConnectResponse(auth_url=auth_url)
    except Exception as e:
        logger.error("Failed to generate connect URL for user_id=%s: %s", current_user.id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate Google connect URL: {e}",
        )


@router.get("/callback")
def callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
) -> RedirectResponse:
    """Handle Google OAuth callback redirect."""
    frontend_base = config.FRONTEND_URL.rstrip("/")
    if error or not code or not state:
        logger.warning("Google OAuth callback error or missing params: error=%s", error)
        return RedirectResponse(
            url=f"{frontend_base}/reminders?google=error",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    try:
        handle_callback(code=code, state=state)
        return RedirectResponse(
            url=f"{frontend_base}/reminders?google=connected",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except Exception as e:
        logger.error("Google OAuth callback failed: %s", e)
        return RedirectResponse(
            url=f"{frontend_base}/reminders?google=error",
            status_code=status.HTTP_303_SEE_OTHER,
        )


@router.post("/disconnect", response_model=GoogleDisconnectResponse)
def disconnect(current_user: User = Depends(get_current_user)) -> GoogleDisconnectResponse:
    """Disconnect Google account for current user and revoke credentials."""
    disconnect_google(current_user.id)
    return GoogleDisconnectResponse(status="ok", disconnected=True)
