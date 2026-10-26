"""Summary flow service: business logic for summaries and TTS.

No Streamlit imports. Pure business logic for API and page use.
"""

from __future__ import annotations

import logging
import uuid
from typing import List, Tuple

from app.database.repositories import DocumentRepository, SummaryRepository
from app.services import summary_service, tts_service
from app.database.models import Summary
from app.utils.config import AUDIO_DIR

logger = logging.getLogger(__name__)


def list_summaries(user_id: int) -> List[Summary]:
    """List all summaries for a user."""
    sum_repo = SummaryRepository()
    return sum_repo.list_for_user(user_id)


def get_or_create_summary(
    user_id: int, doc_id: int, force: bool = False
) -> Summary:
    """Get existing summary for a document or create a new one.

    Args:
        user_id: The user who owns the document.
        doc_id: The document ID to summarize.
        force: If True, generate a new summary even if one exists.

    Returns:
        The Summary object (existing or newly created).

    Raises:
        ValueError: If document not found, not ready, or no text content.
        RuntimeError: If LLM is unavailable or summary generation fails.
    """
    doc_repo = DocumentRepository()
    sum_repo = SummaryRepository()

    doc = doc_repo.get_by_id(doc_id, user_id)
    if not doc:
        raise ValueError("Document not found")
    if doc.status != "ready":
        raise ValueError("Document is not ready for summarization")

    # Get full text from chunks (we don't store full text in DB, only preview)
    # For production, we'd reconstruct from chunks. Use text_preview as source.
    full_text = doc.text_preview or ""
    if not full_text:
        raise ValueError("Document has no text content")

    # Check for existing summary
    existing = sum_repo.list_for_document(doc_id, user_id)
    if existing and not force:
        return existing[0]  # Return most recent

    # Generate new summary
    try:
        summary_text = summary_service.summarize_document(full_text)
    except RuntimeError as e:
        logger.exception("Summary generation failed for doc %s", doc_id)
        raise RuntimeError(str(e))

    if not summary_text:
        raise RuntimeError("Summary generation produced empty result")

    # Save summary
    summary = sum_repo.create(doc_id, user_id, summary_text)
    return summary


def make_audio(user_id: int, summary_id: int) -> Tuple[str, str]:
    """Generate audio for a summary.

    Args:
        user_id: The user who owns the summary.
        summary_id: The summary ID to convert to audio.

    Returns:
        Tuple of (audio_file_path, engine_name).

    Raises:
        ValueError: If summary not found or doesn't belong to user.
        RuntimeError: If TTS generation fails.
    """
    sum_repo = SummaryRepository()

    summary = sum_repo.list_for_user(user_id)
    summary = next((s for s in summary if s.id == summary_id), None)
    if not summary:
        raise ValueError("Summary not found")

    # Ensure user-specific audio directory exists
    user_audio_dir = AUDIO_DIR / str(user_id)
    user_audio_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename
    filename = f"summary_{summary_id}_{uuid.uuid4().hex[:8]}.wav"
    output_path = str(user_audio_dir / filename)

    try:
        audio_path, engine = tts_service.synthesize_with_engine(
            summary.summary_text, filename=output_path
        )
    except RuntimeError as e:
        logger.exception("TTS generation failed for summary %s", summary_id)
        raise RuntimeError(str(e))

    return audio_path, engine
