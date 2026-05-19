"""
Chatbot API — RAG-powered chat with per-user session isolation.

Routes
------
GET    /chatbot/health                          — service health
GET    /chatbot/sessions                        — list user's sessions
POST   /chatbot/sessions                        — create new session
GET    /chatbot/sessions/{session_id}           — get session + messages
DELETE /chatbot/sessions/{session_id}           — delete session
PATCH  /chatbot/sessions/{session_id}/title     — rename session
POST   /chatbot/sessions/{session_id}/messages  — send message, get reply
GET    /chatbot/documents                        — list indexed documents
POST   /chatbot/documents                        — upload & index a PDF
DELETE /chatbot/documents/{doc_id}              — remove a document
"""

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from typing import List

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.repositories.chat_repository import ChatRepository
from app.schemas.chatbot import (
    ChatMessageSchema,
    ChatSessionDetailSchema,
    ChatSessionSchema,
    ChatbotHealthResponse,
    CreateSessionRequest,
    DocumentInfoSchema,
    DocumentUploadResponse,
    SendMessageRequest,
    SendMessageResponse,
    SourceCitation,
    UpdateSessionTitleRequest,
)
from app.schemas.response import APIResponse
from app.services.chatbot_service import get_chatbot_service
from app.services.rag_service import get_rag_service

router = APIRouter(tags=["Chatbot"])
logger = logging.getLogger(__name__)

_MAX_PDF_SIZE_MB = 50
_MAX_PDF_SIZE_BYTES = _MAX_PDF_SIZE_MB * 1024 * 1024


# ── Health ─────────────────────────────────────────────────────────────────────

@router.get(
    "/chatbot/health",
    response_model=APIResponse[ChatbotHealthResponse],
    summary="RAG chatbot health",
)
async def chatbot_health():
    """Get chatbot service health and test RAG retrieval."""
    rag = get_rag_service()
    info = rag.health()
    
    # Test retrieval with a simple query
    test_query = "plant disease"
    test_docs = []
    test_success = False
    try:
        test_docs = rag.search(test_query, k=1, fetch_k=2)
        test_success = len(test_docs) > 0
        logger.debug(f"RAG health check: test query '{test_query}' returned {len(test_docs)} results")
    except Exception as e:
        logger.warning(f"RAG health check: search test failed: {e}")
    
    payload = ChatbotHealthResponse(
        **info,
        is_ready=rag.is_ready(),
    )
    
    # Add test result to response if available
    result_msg = "Chatbot service health"
    if rag.is_ready():
        if test_success:
            result_msg = "Chatbot ready - RAG search functional"
        else:
            result_msg = "Chatbot ready but RAG search may have issues"
    
    return APIResponse.ok(payload, result_msg)


# ── Sessions ───────────────────────────────────────────────────────────────────

@router.get(
    "/chatbot/sessions",
    response_model=APIResponse[List[ChatSessionSchema]],
    summary="List chat sessions for the authenticated user",
)
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = ChatRepository(db)
    sessions = await repo.get_sessions_by_user(current_user.id)
    result = []
    for s in sessions:
        result.append(
            ChatSessionSchema(
                id=s.id,
                title=s.title,
                created_at=s.created_at,
                updated_at=s.updated_at,
                message_count=len(s.messages),
            )
        )
    return APIResponse.ok(result, f"{len(result)} session(s) found")


@router.post(
    "/chatbot/sessions",
    response_model=APIResponse[ChatSessionSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new chat session",
)
async def create_session(
    body: CreateSessionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = ChatRepository(db)
    session = await repo.create_session(current_user.id, body.title)
    return APIResponse.ok(
        ChatSessionSchema(
            id=session.id,
            title=session.title,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=0,
        ),
        "Session created",
    )


@router.get(
    "/chatbot/sessions/{session_id}",
    response_model=APIResponse[ChatSessionDetailSchema],
    summary="Get a session with all its messages",
)
async def get_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = ChatRepository(db)
    session = await repo.get_session(session_id, current_user.id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    messages = [
        ChatMessageSchema(
            id=m.id,
            session_id=m.session_id,
            role=m.role,
            content=m.content,
            sources=[SourceCitation(**s) for s in (m.sources or [])],
            created_at=m.created_at,
        )
        for m in session.messages
    ]
    return APIResponse.ok(
        ChatSessionDetailSchema(
            id=session.id,
            title=session.title,
            created_at=session.created_at,
            updated_at=session.updated_at,
            messages=messages,
        ),
        "Session retrieved",
    )


@router.patch(
    "/chatbot/sessions/{session_id}/title",
    response_model=APIResponse[None],
    summary="Rename a chat session",
)
async def update_session_title(
    session_id: uuid.UUID,
    body: UpdateSessionTitleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = ChatRepository(db)
    updated = await repo.update_session_title(session_id, current_user.id, body.title)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return APIResponse.ok(None, "Title updated")


@router.delete(
    "/chatbot/sessions/{session_id}",
    response_model=APIResponse[None],
    summary="Delete a chat session and all its messages",
)
async def delete_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = ChatRepository(db)
    deleted = await repo.delete_session(session_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return APIResponse.ok(None, "Session deleted")


# ── Messages ───────────────────────────────────────────────────────────────────

@router.post(
    "/chatbot/sessions/{session_id}/messages",
    response_model=APIResponse[SendMessageResponse],
    summary="Send a user message and receive an AI reply",
)
async def send_message(
    session_id: uuid.UUID,
    body: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = ChatRepository(db)

    # Verify session ownership
    session = await repo.get_session(session_id, current_user.id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Persist user message first
    user_msg = await repo.add_message(
        session_id=session_id,
        role="user",
        content=body.message,
    )

    # Fetch recent history (excluding the message we just saved)
    history = await repo.get_recent_messages(session_id, limit=12)
    # Remove the last element (the user msg we just added) from history
    history = [m for m in history if m.id != user_msg.id]

    # Call chatbot service
    try:
        chatbot = get_chatbot_service()
        answer, sources_raw = await chatbot.chat(body.message, history)
    except ValueError as exc:
        logger.error("Chatbot configuration error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Chatbot not available: {exc}",
        ) from exc
    except Exception as exc:
        logger.error("Chatbot inference error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate a response. Please try again.",
        ) from exc

    # Persist assistant message with source citations
    sources_list = [s if isinstance(s, dict) else s for s in sources_raw]
    assistant_msg = await repo.add_message(
        session_id=session_id,
        role="assistant",
        content=answer,
        sources=sources_list,
    )

    # Auto-title the session from the first user message
    if len(session.messages) == 0:
        short_title = body.message[:60].strip()
        if len(body.message) > 60:
            short_title += "…"
        await repo.update_session_title(session_id, current_user.id, short_title)
    else:
        await repo.touch_session(session_id)

    sources_schema = [SourceCitation(**s) for s in sources_list]

    return APIResponse.ok(
        SendMessageResponse(
            user_message=ChatMessageSchema(
                id=user_msg.id,
                session_id=user_msg.session_id,
                role=user_msg.role,
                content=user_msg.content,
                sources=None,
                created_at=user_msg.created_at,
            ),
            assistant_message=ChatMessageSchema(
                id=assistant_msg.id,
                session_id=assistant_msg.session_id,
                role=assistant_msg.role,
                content=assistant_msg.content,
                sources=sources_schema,
                created_at=assistant_msg.created_at,
            ),
            sources=sources_schema,
        ),
        "Response generated",
    )


# ── Documents ──────────────────────────────────────────────────────────────────

@router.get(
    "/chatbot/documents",
    response_model=APIResponse[List[DocumentInfoSchema]],
    summary="List all indexed documents in the knowledge base",
)
async def list_documents(
    current_user: User = Depends(get_current_user),
):
    rag = get_rag_service()
    docs = rag.list_documents()
    result = [
        DocumentInfoSchema(
            id=d["id"],
            name=d["name"],
            pages=d["pages"],
            chunks=d["chunks"],
        )
        for d in docs
    ]
    return APIResponse.ok(result, f"{len(result)} document(s) indexed")


@router.post(
    "/chatbot/documents",
    response_model=APIResponse[DocumentUploadResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload a PDF and add it to the RAG knowledge base",
)
async def upload_document(
    file: UploadFile = File(..., description="PDF file to index (max 50 MB)"),
    current_user: User = Depends(get_current_user),
):
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are accepted",
        )

    content = await file.read()
    if len(content) > _MAX_PDF_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum allowed size is {_MAX_PDF_SIZE_MB} MB.",
        )

    # Save PDF to disk
    upload_dir = Path(settings.RAG_UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename).stem[:100] + ".pdf"
    dest_path = upload_dir / safe_name
    with open(dest_path, "wb") as f:
        f.write(content)

    # Index into ChromaDB
    rag = get_rag_service()
    try:
        already_indexed = False
        import hashlib
        sha = hashlib.sha256(content).hexdigest()
        existing = rag.list_documents()
        for doc in existing:
            if doc.get("hash") == sha:
                already_indexed = True
                doc_info = doc
                break

        if not already_indexed:
            doc_info = rag.load_and_index_pdf(str(dest_path), safe_name.replace(".pdf", ""))

    except Exception as exc:
        logger.error("PDF indexing failed: %s", exc, exc_info=True)
        # Clean up the uploaded file if indexing failed
        try:
            os.remove(dest_path)
        except OSError:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to index document: {exc}",
        ) from exc

    return APIResponse.ok(
        DocumentUploadResponse(
            document=DocumentInfoSchema(
                id=doc_info["id"],
                name=doc_info["name"],
                pages=doc_info["pages"],
                chunks=doc_info["chunks"],
            ),
            already_indexed=already_indexed,
        ),
        "Document indexed successfully" if not already_indexed else "Document was already in the knowledge base",
    )


@router.delete(
    "/chatbot/documents/{doc_id}",
    response_model=APIResponse[None],
    summary="Remove a document from the knowledge base",
)
async def delete_document(
    doc_id: str,
    current_user: User = Depends(get_current_user),
):
    rag = get_rag_service()
    deleted = rag.delete_document(doc_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return APIResponse.ok(None, "Document deleted from knowledge base")
