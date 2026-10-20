"""Chat router: conversations, messages, and RAG Q&A."""

from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.api.schemas import ChatRequest, ChatResponse, ConversationPublic
from app.database.models import User
from app.services import chat_service

router = APIRouter()


@router.post("/api/chat", response_model=ChatResponse)
def api_chat(
    req: ChatRequest,
    user: User = Depends(get_current_user),
):
    """Ask a question via RAG, creating or continuing a conversation."""
    try:
        result = chat_service.ask(user.id, req.question, req.conversation_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RuntimeError as e:
        # LLM unavailable
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    return ChatResponse(
        conversation_id=result.conversation_id,
        answer=result.answer,
        sources=result.sources,
    )


@router.get("/api/conversations", response_model=List[ConversationPublic])
def api_list_conversations(
    user: User = Depends(get_current_user),
):
    """List all conversations for the current user."""
    conversations = chat_service.list_conversations(user.id)
    return [
        ConversationPublic(
            id=c.id,
            user_id=c.user_id,
            title=c.title,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in conversations
    ]


@router.get("/api/conversations/{conversation_id}", response_model=ConversationPublic)
def api_get_conversation(
    conversation_id: int,
    user: User = Depends(get_current_user),
):
    """Get a single conversation by ID."""
    convo = chat_service.get_conversation(user.id, conversation_id)
    if not convo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return ConversationPublic(
        id=convo.id,
        user_id=convo.user_id,
        title=convo.title,
        created_at=convo.created_at,
        updated_at=convo.updated_at,
    )


@router.delete("/api/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def api_delete_conversation(
    conversation_id: int,
    user: User = Depends(get_current_user),
):
    """Delete a conversation and all its messages."""
    chat_service.delete_conversation(user.id, conversation_id)