"""Health check router."""

from __future__ import annotations

from fastapi import APIRouter

from app.services import llm_service

router = APIRouter()


@router.get("/api/health")
def health() -> dict:
    """Health check endpoint (no auth required)."""
    import os
    from app.utils import config
    email_configured = bool(
        os.environ.get("EMAIL_USERNAME", getattr(config, "EMAIL_USERNAME", ""))
        and os.environ.get("EMAIL_APP_PASSWORD", getattr(config, "EMAIL_APP_PASSWORD", ""))
    )
    return {
        "status": "ok",
        "ollama": "up" if llm_service.is_ollama_available() else "down",
        "mock_llm": llm_service.is_mock_mode(),
        "tts_engine": "auto",
        "email_configured": email_configured,
    }