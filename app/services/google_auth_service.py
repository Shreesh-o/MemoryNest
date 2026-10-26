"""Google OAuth and Calendar API service.

Handles user connection/disconnection to Google, token encryption/storage,
CSRF state signing/verification, and authorized Calendar client creation.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from app.api.security import get_jwt_secret
from app.database.repositories import GoogleConnectionRepository
from app.utils import config
from app.utils.security import decrypt_token, encrypt_token

logger = logging.getLogger(__name__)

GOOGLE_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/calendar.events",
]


def is_google_configured() -> bool:
    """Check if Google OAuth is configured via environment variables."""
    return bool(config.GOOGLE_CLIENT_ID and config.GOOGLE_CLIENT_SECRET)


def get_google_status(user_id: int) -> dict[str, Any]:
    """Get the Google integration and connection status for a user."""
    configured = is_google_configured()
    if not configured:
        return {"configured": False, "connected": False, "google_email": None}

    conn = GoogleConnectionRepository().get_by_user_id(user_id)
    if not conn:
        return {"configured": True, "connected": False, "google_email": None}

    return {
        "configured": True,
        "connected": True,
        "google_email": conn.google_email,
    }


def create_oauth_state(user_id: int) -> str:
    """Create a signed, short-lived state JWT containing user_id for CSRF protection."""
    secret = get_jwt_secret()
    payload = {
        "sub": str(user_id),
        "purpose": "google_oauth_state",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def verify_oauth_state(state: str) -> int:
    """Verify signed state token and return user_id.

    Raises:
        ValueError: if invalid, expired, or wrong purpose.
    """
    secret = get_jwt_secret()
    try:
        payload = jwt.decode(state, secret, algorithms=["HS256"])
        if payload.get("purpose") != "google_oauth_state":
            raise ValueError("Invalid OAuth state purpose")
        return int(payload["sub"])
    except jwt.ExpiredSignatureError:
        raise ValueError("OAuth state has expired")
    except Exception as e:
        raise ValueError(f"Invalid OAuth state: {e}")


def _build_flow(state: Optional[str] = None) -> Flow:
    """Build google-auth-oauthlib Flow instance."""
    client_config = {
        "web": {
            "client_id": config.GOOGLE_CLIENT_ID,
            "client_secret": config.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [config.GOOGLE_REDIRECT_URI],
        }
    }
    flow = Flow.from_client_config(
        client_config=client_config,
        scopes=GOOGLE_SCOPES,
        redirect_uri=config.GOOGLE_REDIRECT_URI,
    )
    flow.autogenerate_code_verifier = False
    return flow


def generate_connect_url(user_id: int) -> str:
    """Generate authorization URL for connecting a Google account."""
    if not is_google_configured():
        raise ValueError("Google integration is not configured")

    state = create_oauth_state(user_id)
    flow = _build_flow(state=state)
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        state=state,
    )
    return auth_url


def _extract_email_from_credentials(creds: Credentials) -> Optional[str]:
    """Extract email address from credentials id_token or userinfo endpoint."""
    id_token = getattr(creds, "id_token", None)
    if id_token:
        if isinstance(id_token, dict) and id_token.get("email"):
            return str(id_token["email"])
        if isinstance(id_token, str):
            try:
                payload = jwt.decode(id_token, options={"verify_signature": False})
                if payload.get("email"):
                    return str(payload["email"])
            except Exception:
                pass

    access_token = getattr(creds, "token", None)
    if access_token:
        try:
            import requests

            resp = requests.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=5,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("email"):
                    return str(data["email"])
        except Exception:
            pass
    return None


def handle_callback(code: str, state: str) -> int:
    """Handle OAuth redirect callback, exchange code, store encrypted token.

    Returns:
        user_id on success.

    Raises:
        ValueError: if validation or exchange fails.
    """
    if not is_google_configured():
        raise ValueError("Google integration is not configured")

    user_id = verify_oauth_state(state)
    flow = _build_flow(state=state)
    flow.fetch_token(code=code)
    creds = flow.credentials

    refresh_token = getattr(creds, "refresh_token", None)
    repo = GoogleConnectionRepository()
    if not refresh_token:
        existing = repo.get_by_user_id(user_id)
        if existing:
            refresh_token = decrypt_token(existing.refresh_token_encrypted)
        else:
            raise ValueError("No refresh token received from Google")

    google_email = _extract_email_from_credentials(creds)
    if not google_email:
        existing = repo.get_by_user_id(user_id)
        if existing and existing.google_email:
            google_email = existing.google_email
        else:
            google_email = "connected-user@google.com"

    # Encrypt refresh token with Fernet (never log raw or encrypted token)
    refresh_token_encrypted = encrypt_token(refresh_token)

    scopes_val = getattr(creds, "scopes", None)
    scope_str = ",".join(scopes_val) if scopes_val else ",".join(GOOGLE_SCOPES)

    repo.upsert(
        user_id=user_id,
        google_email=google_email,
        refresh_token_encrypted=refresh_token_encrypted,
        scope=scope_str,
    )
    logger.info("Successfully established Google connection for user_id=%s", user_id)
    return user_id


def disconnect_google(user_id: int) -> bool:
    """Revoke Google refresh token with Google (best effort) and delete the connection."""
    repo = GoogleConnectionRepository()
    conn = repo.get_by_user_id(user_id)
    if not conn:
        return True

    try:
        refresh_token = decrypt_token(conn.refresh_token_encrypted)
        if refresh_token:
            import requests

            requests.post(
                "https://oauth2.googleapis.com/revoke",
                params={"token": refresh_token},
                headers={"content-type": "application/x-www-form-urlencoded"},
                timeout=5,
            )
    except Exception as e:
        logger.warning(
            "Best-effort Google token revocation failed for user_id=%s: %s",
            user_id,
            e,
        )

    repo.delete_by_user_id(user_id)
    logger.info("Deleted Google connection for user_id=%s", user_id)
    return True


def get_calendar_client(user_id: int) -> Optional[Any]:
    """Build an authorized Google Calendar API client for user_id.

    Returns the Google Calendar API client resource, or None if not connected or revoked.
    If the refresh token is revoked or expired (RefreshError), marks the user disconnected.
    """
    if not is_google_configured():
        return None

    repo = GoogleConnectionRepository()
    conn = repo.get_by_user_id(user_id)
    if not conn:
        return None

    try:
        refresh_token = decrypt_token(conn.refresh_token_encrypted)
    except Exception as e:
        logger.error(
            "Failed to decrypt Google refresh token for user_id=%s (%s). Preserving connection record.",
            user_id,
            type(e).__name__,
        )
        return None

    scopes = [s.strip() for s in conn.scope.split(",") if s.strip()] or GOOGLE_SCOPES
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=config.GOOGLE_CLIENT_ID,
        client_secret=config.GOOGLE_CLIENT_SECRET,
        scopes=scopes,
    )

    try:
        creds.refresh(Request())
    except RefreshError:
        logger.warning(
            "Google refresh token revoked or expired for user_id=%s; marking disconnected",
            user_id,
        )
        repo.delete_by_user_id(user_id)
        return None
    except Exception as e:
        logger.error("Error refreshing Google credentials for user_id=%s: %s", user_id, e)
        return None

    try:
        service = build("calendar", "v3", credentials=creds, cache_discovery=False)
        return service
    except Exception as e:
        logger.error("Error building Google Calendar client for user_id=%s: %s", user_id, e)
        return None
