"""Email service for sending reminders via SMTP."""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from typing import Optional

from app.utils.config import (
    EMAIL_HOST, EMAIL_PORT, EMAIL_USERNAME, EMAIL_APP_PASSWORD, RECIPIENT_EMAIL
)


def is_smtp_configured() -> bool:
    """Check if SMTP credentials (username and password) are configured."""
    import app.utils.config as cfg
    username = os.environ.get("EMAIL_USERNAME", getattr(cfg, "EMAIL_USERNAME", ""))
    password = os.environ.get("EMAIL_APP_PASSWORD", getattr(cfg, "EMAIL_APP_PASSWORD", ""))
    return bool(username and password)


def send_reminder_email(subject: str, body: str, to_address: Optional[str] = None) -> tuple[bool, str]:
    """Send a reminder email. Returns (success, detail).

    Recipient is specified via ``to_address``. We stop using the global
    RECIPIENT_EMAIL for user emails, keeping it strictly as a legacy fallback
    when to_address is not provided.
    """
    import app.utils.config as cfg

    username = os.environ.get("EMAIL_USERNAME", getattr(cfg, "EMAIL_USERNAME", ""))
    password = os.environ.get("EMAIL_APP_PASSWORD", getattr(cfg, "EMAIL_APP_PASSWORD", ""))
    host = os.environ.get("EMAIL_HOST", getattr(cfg, "EMAIL_HOST", "smtp.gmail.com"))
    port = int(os.environ.get("EMAIL_PORT", getattr(cfg, "EMAIL_PORT", 587)))

    # Legacy fallback: use global RECIPIENT_EMAIL only if to_address is not provided
    legacy_fallback = os.environ.get("RECIPIENT_EMAIL", getattr(cfg, "RECIPIENT_EMAIL", ""))
    recipient = to_address or legacy_fallback

    if not username or not password:
        return False, "EMAIL_USERNAME or EMAIL_APP_PASSWORD not configured"
    if not recipient:
        return False, "RECIPIENT_EMAIL not configured"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = username
    msg["To"] = recipient
    msg.set_content(body)

    try:
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.starttls()
            server.login(username, password)
            server.send_message(msg)
        return True, "sent"
    except Exception as e:
        return False, f"SMTP error: {e}"


def check_email_config() -> tuple[bool, str]:
    """Verify email config is present."""
    import app.utils.config as cfg

    username = os.environ.get("EMAIL_USERNAME", getattr(cfg, "EMAIL_USERNAME", ""))
    password = os.environ.get("EMAIL_APP_PASSWORD", getattr(cfg, "EMAIL_APP_PASSWORD", ""))
    legacy_fallback = os.environ.get("RECIPIENT_EMAIL", getattr(cfg, "RECIPIENT_EMAIL", ""))

    missing = []
    if not username: missing.append("EMAIL_USERNAME")
    if not password: missing.append("EMAIL_APP_PASSWORD")
    if not legacy_fallback: missing.append("RECIPIENT_EMAIL")
    if missing:
        return False, f"Missing: {', '.join(missing)}"
    return True, "configured"
