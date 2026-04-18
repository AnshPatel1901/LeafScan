"""
RAG API endpoints — document ingestion and querying.

Endpoints:
    POST /rag/documents/upload — upload and ingest PDF
    POST /rag/query — ask a question
    GET /rag/stats — get system statistics
    POST /rag/reset — reset vector database
"""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_db, get_current_user
from app.core.exceptions import AppException, InvalidRequestError
from app.models.user import User
from app.rag.models import RAGConfig, RAGQueryResult
from app.rag.pipeline import get_rag_pipeline
from app.schemas.response import APIResponse

router = APIRouter(prefix="/rag", tags=["RAG"])

logger = logging.getLogger(__name__)


@router.post(
    "/documents/upload",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Upload and ingest PDF document",
    description=(
        "Upload a PDF document for RAG ingestion. "
        "The system will extract text, chunk it, generate embeddings, "
        "and store in the vector database."
    ),
)
async def upload_document(
    file: UploadFile = File(
        ...,
        description="PDF file (max 100 MB)"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    """Upload a PDF document for RAG processing."""
    if not settings.RAG_ENABLED:
        raise InvalidRequestError("RAG system is not enabled in configuration")
    
    if not file or not file.filename:
        raise InvalidRequestError("No file provided")
    
    if not file.filename.lower().endswith('.pdf'):
        raise InvalidRequestError("Only PDF files are supported")
    
    try:
        # Save uploaded file temporarily
        upload_dir = Path(settings.RAG_UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = upload_dir / file.filename
        
        # Save file to disk
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        logger.info(
            "PDF uploaded | user=%s | file=%s | size=%d",
            current_user.id, file.filename, len(content)
        )
        
        # Ingest into RAG system
        rag = get_rag_pipeline()
        result = await rag.ingest_pdf(str(file_path), file.filename)
        
        logger.info("PDF ingestion complete | %s", result)
        
        return APIResponse.ok(
            result,
            f"Document '{file.filename}' ingested successfully"
        )
    
    except AppException:
        raise
    except Exception as exc:
        logger.exception("Document upload failed")
        raise InvalidRequestError(f"Document upload failed: {exc}") from exc


@router.post(
    "/query",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Query the RAG system",
    description=(
        "Ask a question. The system will retrieve relevant documents "
        "and generate an answer using Groq LLM."
    ),
)
async def query_rag(
    query: str = Form(
        ...,
        min_length=3,
        max_length=1000,
        description="Your question",
    ),
    language: str = Form(
        default="en",
        description="Response language (ISO 639-1 code)",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    """Query the RAG system."""
    if not settings.RAG_ENABLED:
        raise InvalidRequestError("RAG system is not enabled in configuration")
    
    query = query.strip()
    if not query:
        raise InvalidRequestError("Query cannot be empty")
    
    try:
        logger.info(
            "RAG query | user=%s | query_len=%d | lang=%s",
            current_user.id, len(query), language
        )
        
        rag = get_rag_pipeline()
        result: RAGQueryResult = await rag.query(query, language=language)
        
        # Format response
        response_data = {
            "query": result.query,
            "answer": result.answer,
            "language": result.language,
            "sources": result.sources,
            "num_documents": len(result.documents),
            "query_time_ms": round(result.query_time_ms, 2),
            "generation_time_ms": round(result.generation_time_ms, 2),
            "total_time_ms": round(result.total_time_ms, 2),
        }
        
        # Include documents if requested
        if result.documents:
            response_data["documents"] = [
                {
                    "source": doc.source,
                    "page": doc.page,
                    "score": round(doc.score, 3) if doc.score else None,
                    "preview": doc.content[:200] + "..." if len(doc.content) > 200 else doc.content,
                }
                for doc in result.documents
            ]
        
        logger.info("RAG query complete | answer_len=%d", len(result.answer))
        
        return APIResponse.ok(
            response_data,
            "Query answered successfully"
        )
    
    except AppException:
        raise
    except Exception as exc:
        logger.exception("RAG query failed")
        raise InvalidRequestError(f"Query failed: {exc}") from exc


@router.get(
    "/stats",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Get RAG system statistics",
)
async def get_stats(
    current_user: User = Depends(get_current_user),
) -> APIResponse[dict]:
    """Get RAG system statistics."""
    if not settings.RAG_ENABLED:
        raise InvalidRequestError("RAG system is not enabled in configuration")
    
    try:
        rag = get_rag_pipeline()
        stats = await rag.get_stats()
        
        return APIResponse.ok(stats, "Statistics retrieved successfully")
    
    except Exception as exc:
        logger.exception("Failed to get stats")
        raise InvalidRequestError(f"Failed to get stats: {exc}") from exc


@router.post(
    "/reset",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Reset RAG system",
    description="Delete all documents from vector database (admin only)",
)
async def reset_rag(
    current_user: User = Depends(get_current_user),
) -> APIResponse[dict]:
    """Reset RAG system (delete all documents)."""
    if not settings.RAG_ENABLED:
        raise InvalidRequestError("RAG system is not enabled in configuration")
    
    try:
        logger.warning("RAG reset requested by user=%s", current_user.id)
        
        rag = get_rag_pipeline()
        success = await rag.reset()
        
        if success:
            return APIResponse.ok(
                {"status": "reset_complete"},
                "RAG system reset successfully"
            )
        else:
            raise InvalidRequestError("Failed to reset RAG system")
    
    except AppException:
        raise
    except Exception as exc:
        logger.exception("RAG reset failed")
        raise InvalidRequestError(f"Reset failed: {exc}") from exc
