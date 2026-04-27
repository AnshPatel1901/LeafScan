"""
Pydantic schemas for the chatbot API.
Every response is wrapped in the standard APIResponse[T] envelope.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Source citation ────────────────────────────────────────────────────────────

class SourceCitation(BaseModel):
    source: str
    page: Optional[int] = None
    preview: Optional[str] = None


# ── Messages ───────────────────────────────────────────────────────────────────

class ChatMessageSchema(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    role: str  # "user" | "assistant"
    content: str
    sources: Optional[List[SourceCitation]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Sessions ───────────────────────────────────────────────────────────────────

class ChatSessionSchema(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    model_config = {"from_attributes": True}


class ChatSessionDetailSchema(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[ChatMessageSchema] = []

    model_config = {"from_attributes": True}


# ── Request bodies ─────────────────────────────────────────────────────────────

class CreateSessionRequest(BaseModel):
    title: str = Field(default="New Chat", max_length=256)


class SendMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000, description="User message text")


class UpdateSessionTitleRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=256)


# ── Response payloads ──────────────────────────────────────────────────────────

class SendMessageResponse(BaseModel):
    user_message: ChatMessageSchema
    assistant_message: ChatMessageSchema
    sources: List[SourceCitation] = []


class DocumentInfoSchema(BaseModel):
    id: str
    name: str
    pages: int
    chunks: int


class DocumentUploadResponse(BaseModel):
    document: DocumentInfoSchema
    already_indexed: bool = False


class ChatbotHealthResponse(BaseModel):
    initialized: bool
    documents_indexed: int
    vector_db_dir: str
    upload_dir: str
    embedding_model: str
    groq_model: str
    is_ready: bool
