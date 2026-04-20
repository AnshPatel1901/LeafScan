"""
Text-to-Speech audio endpoint — GET /tts/audio/{filename}.

Serves pre-generated TTS audio files with streaming support.
Allows frontend to pause/stop audio playback client-side.
"""

import logging
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.config import settings

router = APIRouter(tags=["TTS"])
logger = logging.getLogger(__name__)


@router.get(
    "/audio/{filename}",
    response_class=StreamingResponse,
    summary="Stream TTS audio file",
    description=(
        "Retrieve a pre-generated TTS audio file for streaming to the client. "
        "The frontend can control playback (pause/stop) client-side. "
        "Supports range requests for seeking through audio."
    ),
    responses={
        200: {
            "description": "MP3 audio stream",
            "content": {"audio/mpeg": {}},
        },
        404: {
            "description": "Audio file not found",
        },
        400: {
            "description": "Invalid filename",
        },
    },
)
async def get_tts_audio(filename: str) -> StreamingResponse:
    """
    Stream TTS audio file to client.
    
    Parameters
    ----------
    filename : str
        Audio filename (e.g., 'abc123_hi.mp3')
        
    Returns
    -------
    StreamingResponse
        MP3 audio stream with proper headers for seeking

    Raises
    ------
    HTTPException
        - 400: Invalid filename (contains path traversal attempts)
        - 404: File not found
    """
    # ── Security: Prevent path traversal attacks ──────────────────────────────
    if ".." in filename or "/" in filename or "\\" in filename:
        logger.warning("Path traversal attempt detected: %s", filename)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename",
        )

    # ── Validate file extension ───────────────────────────────────────────────
    if not filename.endswith(".mp3"):
        logger.warning("Invalid file extension attempted: %s", filename)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only MP3 files are supported",
        )

    # ── Construct safe file path ──────────────────────────────────────────────
    # Use absolute path to avoid working directory issues
    file_path = Path(settings.tts_storage_dir_absolute) / filename
    
    # Double-check that resolved path is within TTS_STORAGE_DIR (defense-in-depth)
    try:
        file_path = file_path.resolve()
        storage_dir = Path(settings.tts_storage_dir_absolute).resolve()
        if not str(file_path).startswith(str(storage_dir)):
            logger.warning("Path traversal detected after resolution: %s", filename)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid filename",
            )
    except (OSError, ValueError) as exc:
        logger.error("Path resolution error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename",
        ) from exc

    # ── Check if file exists ──────────────────────────────────────────────────
    if not file_path.exists() or not file_path.is_file():
        logger.warning("Audio file not found: %s", file_path)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audio file not found: {filename}",
        )

    # ── Get file size for headers ────────────────────────────────────────────
    file_size = file_path.stat().st_size
    logger.debug("Serving audio file: %s (%d bytes)", filename, file_size)

    # ── Stream audio file with proper headers ────────────────────────────────
    async def audio_stream():
        """Stream audio file in chunks."""
        try:
            with open(file_path, "rb") as f:
                # Stream in 256KB chunks
                chunk_size = 256 * 1024
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
        except IOError as exc:
            logger.error("Error streaming audio file: %s", exc)
            # Client will hear audio up to error point
            raise

    return StreamingResponse(
        audio_stream(),
        media_type="audio/mpeg",
        headers={
            "Content-Length": str(file_size),
            "Content-Disposition": f"inline; filename={filename}",
            "Cache-Control": "public, max-age=86400",  # Cache for 24 hours
            "Accept-Ranges": "bytes",  # Allow seeking
        },
    )


# ── Health check for TTS storage ─────────────────────────────────────────────


@router.get(
    "/health",
    summary="Check TTS service health",
    description="Verify TTS configuration and storage directory is accessible.",
    responses={
        200: {"description": "TTS service is healthy"},
        503: {"description": "TTS service is unavailable"},
    },
)
async def tts_health() -> dict:
    """
    Check TTS service health and configuration.
    
    Returns
    -------
    dict
        Health status, configuration status, and storage directory info
    """
    try:
        # Check TTS enabled
        is_tts_enabled = settings.TTS_ENABLED
        has_api_key = bool(settings.GOOGLE_TTS_API_KEY)
        
        storage_path = Path(settings.TTS_STORAGE_DIR)
        
        # Check if directory exists and is readable
        if not storage_path.exists():
            logger.warning("TTS storage directory does not exist: %s", storage_path)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="TTS storage directory not accessible",
            )

        # Count audio files
        audio_files = list(storage_path.glob("*.mp3"))
        
        # Determine status
        status_msg = "healthy"
        if is_tts_enabled and not has_api_key:
            status_msg = "degraded"
        
        logger.debug(
            "TTS health check: enabled=%s, api_key=%s, files=%d",
            is_tts_enabled,
            "configured" if has_api_key else "missing",
            len(audio_files),
        )
        
        return {
            "status": status_msg,
            "tts_enabled": is_tts_enabled,
            "sarvam_ai_api_key_configured": has_api_key,
            "tts_provider": "Sarvam AI (Bulbul v2)",
            "storage_directory": str(storage_path),
            "audio_files_cached": len(audio_files),
            "disk_space_available_mb": (
                os.statvfs(storage_path).f_bavail * os.statvfs(storage_path).f_frsize / (1024 * 1024)
                if os.path.exists(storage_path)
                else 0
            ),
            "supported_languages": [
                "en", "hi", "ta", "te", "kn", "ml"
            ],
            "message": (
                "TTS fully operational (Sarvam AI Bulbul v2)" if (is_tts_enabled and has_api_key)
                else "TTS disabled or API key missing" if is_tts_enabled
                else "TTS disabled (set TTS_ENABLED=true in .env to enable)"
            ),
        }

    except Exception as exc:
        logger.error("TTS health check failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TTS service health check failed",
        ) from exc
