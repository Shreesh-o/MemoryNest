"""Chat service: conversation management and RAG integration.

No Streamlit imports. Pure business logic for API and page use.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from app.database.repositories import ConversationRepository, MessageRepository
from app.database.models import Conversation, Message
from app.services import rag_service


@dataclass
class ChatResult:
    conversation_id: int
    answer: str
    sources: List[dict]


def _generate_title_from_question(question: str, max_len: int = 50) -> str:
    """Generate a conversation title from the first question."""
    title = question.strip()
    if len(title) > max_len:
        title = title[:max_len].rstrip() + "..."
    return title


def ask(
    user_id: int,
    question: str,
    conversation_id: Optional[int] = None,
) -> ChatResult:
    """Ask a question in a conversation (create new if needed).

    Saves the user message, gets RAG answer, saves assistant message with sources.

    Args:
        user_id: The user asking the question.
        question: The question text (max 2000 chars enforced by caller).
        conversation_id: Optional existing conversation ID. If None, creates new.

    Returns:
        ChatResult with conversation_id, answer, and sources.

    Raises:
        ValueError: If question is empty or conversation not found.
        RuntimeError: If LLM is unavailable (propagated from rag_service/llm_service).
    """
    question = question.strip()
    if not question:
        raise ValueError("Question cannot be empty")

    convo_repo = ConversationRepository()
    msg_repo = MessageRepository()

    # Get or create conversation
    if conversation_id is not None:
        convo = convo_repo.get_by_id(conversation_id, user_id)
        if not convo:
            raise ValueError("Conversation not found")
    else:
        title = _generate_title_from_question(question)
        convo = convo_repo.create(user_id, title)
        conversation_id = convo.id

    # Save user message
    msg_repo.create(
        conversation_id=conversation_id,
        user_id=user_id,
        role="user",
        content=question,
        sources=None,
    )

    # Get RAG answer
    result = rag_service.rag_answer(user_id, question)

    # Save assistant message with sources
    msg_repo.create(
        conversation_id=conversation_id,
        user_id=user_id,
        role="assistant",
        content=result.answer,
        sources=result.sources,
    )

    # Update conversation title if it's the first exchange (default title)
    if convo.title is None or convo.title == "Untitled":
        new_title = _generate_title_from_question(question)
        ConversationRepository().update_title(conversation_id, user_id, new_title)

    return ChatResult(
        conversation_id=conversation_id,
        answer=result.answer,
        sources=result.sources,
    )


def list_conversations(user_id: int) -> List[Conversation]:
    """List all conversations for a user."""
    return ConversationRepository().list_for_user(user_id)


def get_conversation(user_id: int, conversation_id: int) -> Optional[Conversation]:
    """Get a conversation with its messages."""
    convo_repo = ConversationRepository()
    msg_repo = MessageRepository()

    convo = convo_repo.get_by_id(conversation_id, user_id)
    if not convo:
        return None

    messages = msg_repo.list_for_conversation(conversation_id, user_id)
    # We don't attach messages to the dataclass; caller can fetch separately
    return convo


def get_conversation_with_messages(user_id: int, conversation_id: int) -> Optional[tuple[Conversation, list[Message]]]:
    """Get a conversation with its messages."""
    convo_repo = ConversationRepository()
    msg_repo = MessageRepository()

    convo = convo_repo.get_by_id(conversation_id, user_id)
    if not convo:
        return None

    messages = msg_repo.list_for_conversation(conversation_id, user_id)
    return convo, messages


def delete_conversation(user_id: int, conversation_id: int) -> None:
    """Delete a conversation and its messages (cascades via FK)."""
    ConversationRepository().delete(conversation_id, user_id)