"""Pydantic schemas for the FastAPI layer."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class UserPublic(BaseModel):
    id: int
    username: str
    email: Optional[str] = None


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class DocumentPublic(BaseModel):
    id: int
    filename: str
    file_type: str
    status: str
    chunk_count: int
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    text_preview: Optional[str] = None


class IngestResultResponse(BaseModel):
    filename: str
    status: str
    message: str
    doc_id: Optional[int] = None
    chunk_count: int