"""Health check router."""

from __future__ import annotations

from fastapi import APIRouter

from app.services import llm_service

router = APIRouter()


@router.get("/api/health")
def health() -> dict:
    """Health check endpoint (no auth required)."""
    return {
        "status": "ok",
        "ollama": "up" if llm_service.is_ollama_available() else "down",
        "mock_llm": llm_service.is_mock_mode(),
        "tts_engine": "auto",
    }