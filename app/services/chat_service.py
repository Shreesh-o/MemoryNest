"""Chat service: conversation management and RAG integration.

No Streamlit imports. Pure business logic for API and page use.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from app.database.repositories import ConversationRepository, MessageRepository, DocumentRepository
from app.database.models import Conversation, Message, Document
from app.services import rag_service


class DocumentValidationError(Exception):
    """Validation error for document selection (empty or exceeds cap)."""
    pass


class DocumentNotFoundError(Exception):
    """Document not found or belongs to another user."""
    pass


class DocumentNotReadyError(Exception):
    """Document is not in ready status."""
    pass


@dataclass
class ChatResult:
    conversation_id: int
    answer: str
    sources: List[dict]
    scope: Optional[dict] = None


def validate_and_resolve_document_ids(
    user_id: int,
    document_ids: Optional[List[int]],
) -> Optional[List[int]]:
    """Validate document_ids:
    - None -> returns None (all documents)
    - empty list -> raises DocumentValidationError (422)
    - length > 200 -> raises DocumentValidationError (422)
    - unknown or foreign id -> raises DocumentNotFoundError (404)
    - not ready -> raises DocumentNotReadyError (400)
    """
    if document_ids is None:
        return None

    if len(document_ids) == 0:
        raise DocumentValidationError("select at least one document")

    if len(document_ids) > 200:
        raise DocumentValidationError("Cannot select more than 200 documents")

    # Deduplicate while preserving order
    unique_ids = list(dict.fromkeys(document_ids))

    doc_repo = DocumentRepository()
    docs = doc_repo.get_by_ids(unique_ids, user_id)
    found_map = {d.id: d for d in docs}

    # Any ID not found for this user (foreign or non-existent)
    missing = [did for did in unique_ids if did not in found_map]
    if missing:
        raise DocumentNotFoundError("One or more selected documents not found")

    # Any ID not ready
    not_ready = [d for d in docs if d.status != "ready"]
    if not_ready:
        raise DocumentNotReadyError(
            f"Document '{not_ready[0].filename}' is not ready (status: {not_ready[0].status})"
        )

    return unique_ids


def list_ready_documents(user_id: int) -> List[Document]:
    """List ready documents for the user."""
    return DocumentRepository().list_ready_for_user(user_id)


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
    document_ids: Optional[List[int]] = None,
) -> ChatResult:
    """Ask a question in a conversation (create new if needed).

    Saves the user message, gets RAG answer, saves assistant message with sources and scope.

    Args:
        user_id: The user asking the question.
        question: The question text (max 2000 chars enforced by caller).
        conversation_id: Optional existing conversation ID. If None, creates new.
        document_ids: Optional list of document IDs to scope the search to.

    Returns:
        ChatResult with conversation_id, answer, sources, and scope.

    Raises:
        ValueError: If question is empty or conversation not found.
        DocumentValidationError: If document_ids is empty list or exceeds cap.
        DocumentNotFoundError: If document_ids contains non-existent or foreign IDs.
        DocumentNotReadyError: If document_ids contains documents not in 'ready' status.
        RuntimeError: If LLM is unavailable (propagated from rag_service/llm_service).
    """
    question = question.strip()
    if not question:
        raise ValueError("Question cannot be empty")

    # Validate and resolve document selection
    validated_doc_ids = validate_and_resolve_document_ids(user_id, document_ids)

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
    result = rag_service.rag_answer(user_id, question, document_ids=validated_doc_ids)

    # Save assistant message with sources and scope
    msg_repo.create(
        conversation_id=conversation_id,
        user_id=user_id,
        role="assistant",
        content=result.answer,
        sources=result.sources,
        scope=result.scope,
    )

    # Update conversation title if it's the first exchange (default title)
    if convo.title is None or convo.title == "Untitled":
        new_title = _generate_title_from_question(question)
        ConversationRepository().update_title(conversation_id, user_id, new_title)

    return ChatResult(
        conversation_id=conversation_id,
        answer=result.answer,
        sources=result.sources,
        scope=result.scope,
    )


def list_conversations(user_id: int) -> List[Conversation]:
    """List all conversations for a user."""
    return ConversationRepository().list_for_user(user_id)


def get_conversation(user_id: int, conversation_id: int) -> Optional[Conversation]:
    """Get a conversation."""
    convo_repo = ConversationRepository()
    convo = convo_repo.get_by_id(conversation_id, user_id)
    if not convo:
        return None
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