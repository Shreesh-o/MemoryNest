"""Summaries router: list, generate, and audio for summaries."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.api.deps import get_current_user
from app.api.schemas import SummaryAudioResponse, SummaryCreateRequest, SummaryPublic
from app.database.models import User
from app.services.summary_flow_service import (
    get_or_create_summary,
    list_summaries,
    make_audio,
)

router = APIRouter()


def _summary_to_public(s) -> SummaryPublic:
    return SummaryPublic(
        id=s.id,
        document_id=s.document_id,
        user_id=s.user_id,
        summary_text=s.summary_text,
        created_at=s.created_at,
    )


@router.get("/api/summaries", response_model=list[SummaryPublic])
def api_list_summaries(user: User = Depends(get_current_user)):
    """List all summaries for the current user."""
    summaries = list_summaries(user.id)
    return [_summary_to_public(s) for s in summaries]


@router.post("/api/documents/{doc_id}/summary", response_model=SummaryPublic)
def api_create_summary(
    doc_id: int,
    req: SummaryCreateRequest,
    user: User = Depends(get_current_user),
):
    """Generate or retrieve a summary for a document."""
    try:
        summary = get_or_create_summary(user.id, doc_id, req.force)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RuntimeError as e:
        # LLM unavailable
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    return _summary_to_public(summary)


@router.post("/api/summaries/{summary_id}/audio", response_model=SummaryAudioResponse)
def api_generate_summary_audio(
    summary_id: int,
    user: User = Depends(get_current_user),
):
    """Generate audio for a summary."""
    try:
        audio_path, engine = make_audio(user.id, summary_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RuntimeError as e:
        # TTS failure
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))

    # Return relative URL for the audio file
    # The file is at AUDIO_DIR/<user_id>/filename.wav
    # We'll serve it via a separate endpoint
    filename = Path(audio_path).name
    url = f"/api/summaries/{summary_id}/audio/file"
    return SummaryAudioResponse(engine=engine, url=url)


@router.get("/api/summaries/{summary_id}/audio")
def api_get_summary_audio(
    summary_id: int,
    user: User = Depends(get_current_user),
):
    """Serve the audio file for a summary."""
    from app.services.summary_flow_service import make_audio
    from app.database.repositories import SummaryRepository

    # First verify the summary belongs to the user
    sum_repo = SummaryRepository()
    summary = sum_repo.list_for_user(user.id)
    summary = next((s for s in summary if s.id == summary_id), None)
    if not summary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Summary not found")

    # Check if audio file already exists
    from app.utils.config import AUDIO_DIR
    user_audio_dir = AUDIO_DIR / str(user.id)
    # Look for existing audio file for this summary
    audio_files = list(user_audio_dir.glob(f"summary_{summary_id}_*.wav"))
    if not audio_files:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio not found. Generate it first.")

    audio_path = audio_files[0]  # Use the most recent one
    return FileResponse(
        path=str(audio_path),
        media_type="audio/wav",
        filename=f"summary_{summary_id}.wav",
    )


@router.get("/api/summaries/{summary_id}/audio/file")
def api_get_summary_audio_file(
    summary_id: int,
    user: User = Depends(get_current_user),
):
    """Serve the audio file for a summary (alias for the audio endpoint)."""
    from app.database.repositories import SummaryRepository
    from app.utils.config import AUDIO_DIR

    # First verify the summary belongs to the user
    sum_repo = SummaryRepository()
    summary = sum_repo.list_for_user(user.id)
    summary = next((s for s in summary if s.id == summary_id), None)
    if not summary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Summary not found")

    # Check if audio file already exists
    user_audio_dir = AUDIO_DIR / str(user.id)
    # Look for existing audio file for this summary
    audio_files = list(user_audio_dir.glob(f"summary_{summary_id}_*.wav"))
    if not audio_files:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio not found. Generate it first.")

    audio_path = audio_files[0]  # Use the most recent one
    return FileResponse(
        path=str(audio_path),
        media_type="audio/wav",
        filename=f"summary_{summary_id}.wav",
    )