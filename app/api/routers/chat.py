"""Chat router: conversations, messages, and RAG Q&A."""

from __future__ import annotations

import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.api.schemas import (
    ChatDocumentItem,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ConversationPublic,
)
from app.database.models import User
from app.services import chat_service
from app.services.chat_service import (
    DocumentNotFoundError,
    DocumentNotReadyError,
    DocumentValidationError,
)

router = APIRouter()


@router.post("/api/chat", response_model=ChatResponse)
def api_chat(
    req: ChatRequest,
    user: User = Depends(get_current_user),
):
    """Ask a question via RAG, creating or continuing a conversation."""
    try:
        result = chat_service.ask(
            user.id,
            req.question,
            req.conversation_id,
            req.document_ids,
        )
    except DocumentValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DocumentNotReadyError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RuntimeError as e:
        # LLM unavailable
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    return ChatResponse(
        conversation_id=result.conversation_id,
        answer=result.answer,
        sources=result.sources,
        scope=result.scope,
    )


@router.get("/api/chat/documents", response_model=List[ChatDocumentItem])
def api_chat_documents(
    user: User = Depends(get_current_user),
):
    """Return a lightweight list of ready documents for scoping the chat."""
    docs = chat_service.list_ready_documents(user.id)
    return [
        ChatDocumentItem(
            id=d.id,
            filename=d.filename,
            file_type=d.file_type,
        )
        for d in docs
    ]


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
    """Get a single conversation by ID with its messages."""
    convo_with_msgs = chat_service.get_conversation_with_messages(user.id, conversation_id)
    if not convo_with_msgs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    convo, messages = convo_with_msgs

    parsed_messages = []
    for m in messages:
        sources_list = None
        if m.sources:
            try:
                sources_list = json.loads(m.sources)
            except Exception:
                sources_list = None
        scope_dict = None
        if m.scope:
            try:
                scope_dict = json.loads(m.scope)
            except Exception:
                scope_dict = None
        parsed_messages.append(
            ChatMessage(
                role=m.role,
                content=m.content,
                sources=sources_list,
                scope=scope_dict,
                created_at=m.created_at,
            )
        )

    return ConversationPublic(
        id=convo.id,
        user_id=convo.user_id,
        title=convo.title,
        created_at=convo.created_at,
        updated_at=convo.updated_at,
        messages=parsed_messages,
    )


@router.get("/api/conversations/{conversation_id}/messages", response_model=List[ChatMessage])
def api_get_conversation_messages(
    conversation_id: int,
    user: User = Depends(get_current_user),
):
    """Get all messages for a conversation including sources and scope."""
    convo_with_msgs = chat_service.get_conversation_with_messages(user.id, conversation_id)
    if not convo_with_msgs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    _, messages = convo_with_msgs

    parsed_messages = []
    for m in messages:
        sources_list = None
        if m.sources:
            try:
                sources_list = json.loads(m.sources)
            except Exception:
                sources_list = None
        scope_dict = None
        if m.scope:
            try:
                scope_dict = json.loads(m.scope)
            except Exception:
                scope_dict = None
        parsed_messages.append(
            ChatMessage(
                role=m.role,
                content=m.content,
                sources=sources_list,
                scope=scope_dict,
                created_at=m.created_at,
            )
        )
    return parsed_messages


@router.delete("/api/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def api_delete_conversation(
    conversation_id: int,
    user: User = Depends(get_current_user),
):
    """Delete a conversation and all its messages."""
    chat_service.delete_conversation(user.id, conversation_id)