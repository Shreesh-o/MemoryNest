"""Email service for sending reminders via SMTP."""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage

from app.utils.config import (
    EMAIL_HOST, EMAIL_PORT, EMAIL_USERNAME, EMAIL_APP_PASSWORD, RECIPIENT_EMAIL
)


def send_reminder_email(subject: str, body: str) -> tuple[bool, str]:
    """Send a reminder email. Returns (success, detail)."""
    if not EMAIL_USERNAME or not EMAIL_APP_PASSWORD:
        return False, "EMAIL_USERNAME or EMAIL_APP_PASSWORD not configured"
    if not RECIPIENT_EMAIL:
        return False, "RECIPIENT_EMAIL not configured"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = EMAIL_USERNAME
    msg["To"] = RECIPIENT_EMAIL
    msg.set_content(body)

    try:
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT, timeout=30) as server:
            server.starttls()
            server.login(EMAIL_USERNAME, EMAIL_APP_PASSWORD)
            server.send_message(msg)
        return True, "sent"
    except Exception as e:
        return False, f"SMTP error: {e}"


def check_email_config() -> tuple[bool, str]:
    """Verify email config is present."""
    missing = []
    if not EMAIL_USERNAME: missing.append("EMAIL_USERNAME")
    if not EMAIL_APP_PASSWORD: missing.append("EMAIL_APP_PASSWORD")
    if not RECIPIENT_EMAIL: missing.append("RECIPIENT_EMAIL")
    if missing:
        return False, f"Missing: {', '.join(missing)}"
    return True, "configured"