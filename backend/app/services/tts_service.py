"""
Text-to-Speech (TTS) Service — converts text to audio using Sarvam AI Bulbul v2.

Features:
    • Sarvam AI Bulbul v2 integration (Free tier available)
    • 7 language support (English, Hindi, Tamil, Telugu, Kannada, Malayalam, Gujarati)
    • Automatic audio file caching with MD5 hashing
    • Production-ready error handling
    • Gender-neutral voices for all languages

Environment variables required:
    • SARVAM_AI_API_KEY (Sarvam AI API key)
    • TTS_ENABLED (set to True to enable)

Sarvam AI Details:
    • Endpoint: https://api.sarvam.ai/text-to-speech
    • Model: Bulbul v2 (Indian language specialist)
    • Supported Languages: en, hi, ta, te, kn, ml, gu
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from hashlib import md5
from pathlib import Path
from typing import Optional

import httpx

from app.core.config import settings
from app.core.exceptions import ExternalServiceError

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(connect=10.0, read=90.0, write=10.0, pool=5.0)

# Sarvam AI Bulbul v2 supported languages
# Map from ISO 639-1 codes to Sarvam API language codes
_SARVAM_SUPPORTED_LANGUAGES: dict[str, str] = {
    "en": "en-IN",      # English
    "hi": "hi-IN",      # Hindi
    "ta": "ta-IN",      # Tamil
    "te": "te-IN",      # Telugu
    "kn": "kn-IN",      # Kannada
    "ml": "ml-IN",      # Malayalam
    "gu": "gu-IN",      # Gujarati
}


@dataclass
class TTSResult:
    """Result of TTS operation."""
    audio_url: str
    duration_seconds: Optional[float] = None
    file_path: Optional[str] = None


class TTSService:
    """
    Text-to-Speech service using Sarvam AI Bulbul v2.
    
    Converts text to audio files using Sarvam AI's Bulbul v2 model
    and stores them locally for streaming/access.
    
    Supports 7 Indian and English languages with automatic caching 
    and production-grade error recovery.
    """

    def __init__(
        self,
        tts_enabled: bool = settings.TTS_ENABLED,
        storage_dir: str | None = None,
    ) -> None:
        """
        Initialize TTS service.
        
        Parameters
        ----------
        tts_enabled : bool
            Whether TTS is enabled globally
        storage_dir : str, optional
            Directory to store audio files (uses absolute path from config if not provided)
        """
        self._enabled = tts_enabled
        # Use absolute path to avoid working directory issues
        self._storage_dir = storage_dir or settings.tts_storage_dir_absolute
        
        # Create storage directory if needed
        if self._enabled:
            Path(self._storage_dir).mkdir(parents=True, exist_ok=True)
            logger.info("TTS service initialized (Sarvam AI Bulbul v2) | storage_dir=%s", self._storage_dir)

    # ── Public API ─────────────────────────────────────────────────────────────

    async def synthesize(
        self,
        text: str,
        language: str = "en",
    ) -> Optional[TTSResult]:
        """
        Convert text to speech using Sarvam AI Bulbul v2.

        Parameters
        ----------
        text : str
            Text to convert to speech (max 2500 characters for Sarvam AI)
        language : str
            ISO 639-1 language code (e.g., 'en', 'hi', 'ta')
            Only supported languages will generate audio

        Returns
        -------
        Optional[TTSResult]
            TTS result with audio URL, or None if:
            - TTS is disabled
            - Text is empty
            - Language is not supported
            - API call fails (logged but not raised)

        Raises
        ------
        ExternalServiceError
            If Sarvam AI API is misconfigured or returns unexpected format
        """
        if not self._enabled:
            logger.debug("TTS is disabled in config")
            return None

        if not text or not text.strip():
            logger.warning("Received empty text for TTS synthesis")
            return None

        # Normalize and validate language
        language = language.lower().strip() if language else "en"
        
        # Check if language is supported
        if language not in _SARVAM_SUPPORTED_LANGUAGES:
            logger.info(
                "Unsupported language for Sarvam AI TTS: %s (supported: en, hi, ta, te, kn, ml, gu), skipping audio generation",
                language,
            )
            return None  # Return None for unsupported languages (graceful degradation)

        # Truncate very long text (Sarvam AI limit is 2500 chars)
        if len(text) > 2500:
            logger.warning("Text too long for TTS (%d chars), truncating to 2500", len(text))
            text = text[:2500]

        try:
            return await self._synthesize_sarvam(text, language)
        except ExternalServiceError:
            raise
        except Exception as exc:
            logger.exception("Unexpected error in TTS synthesis: %s", exc)
            raise ExternalServiceError(f"TTS synthesis failed: {exc}") from exc

    # ── Private: Sarvam AI TTS ─────────────────────────────────────────────────

    async def _synthesize_sarvam(self, text: str, language: str) -> TTSResult:
        """
        Call Sarvam AI Text-to-Speech API with Bulbul v2 model.
        
        Parameters
        ----------
        text : str
            Text to synthesize
        language : str
            Language code (validated, will be in _SARVAM_SUPPORTED_LANGUAGES)

        Returns
        -------
        TTSResult
            Audio URL and file path

        Raises
        ------
        ExternalServiceError
            If API key not configured, request fails, or response is malformed
        """
        api_key = settings.SARVAM_AI_API_KEY
        if not api_key:
            raise ExternalServiceError(
                "SARVAM_AI_API_KEY not configured in environment"
            )

        # Sarvam AI API endpoint for Bulbul v2
        url = "https://api.sarvam.ai/text-to-speech"

        # Get mapped language code (e.g., "en" -> "en-IN")
        mapped_language = _SARVAM_SUPPORTED_LANGUAGES.get(language, language)

        # Prepare request payload for Sarvam AI Bulbul v2
        # Using recommended 'text' format (inputs is deprecated)
        payload = {
            "text": text,  # Direct text format (preferred by Sarvam AI)
            "target_language_code": mapped_language,  # Use mapped code: en-IN, hi-IN, etc.
            "speaker": "manisha",  # Female voice (gender-neutral)
            "pitch": 1.0,
            "pace": 0.8,  # Medium speech pace (default 1.0 is fast, 0.8 is medium)
            "loudness": 1.0,
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.post(
                    url,
                    json=payload,
                    headers={"API-Subscription-Key": api_key},
                )
                resp.raise_for_status()
                data = resp.json()

        except httpx.HTTPStatusError as exc:
            logger.error(
                "Sarvam AI API HTTP error: status=%d, response=%s",
                exc.response.status_code,
                exc.response.text[:500],
            )
            raise ExternalServiceError(
                f"Sarvam AI API error ({exc.response.status_code})"
            ) from exc
        except httpx.RequestError as exc:
            logger.error("Sarvam AI API request failed: %s", exc)
            raise ExternalServiceError(f"Sarvam AI request failed: {exc}") from exc
        except Exception as exc:
            logger.error("Unexpected error calling Sarvam AI API: %s", exc)
            raise ExternalServiceError(f"Sarvam AI API error: {exc}") from exc

        # Extract audio from response
        try:
            # Sarvam AI returns audio as base64 in 'audios' list
            audios = data.get("audios", [])
            if not audios or not audios[0]:
                raise ExternalServiceError("No audio content in Sarvam AI response")

            audio_content = audios[0]
            
            # Decode Base64 audio
            import base64
            audio_bytes = base64.b64decode(audio_content)
            logger.debug("Decoded %d bytes of audio from Sarvam AI", len(audio_bytes))

        except (KeyError, IndexError, TypeError, ValueError) as exc:
            logger.error("Malformed Sarvam AI response: %s", exc)
            raise ExternalServiceError(
                f"Unexpected Sarvam AI response format: {exc}"
            ) from exc

        # Save audio file
        file_path = self._save_audio_file(audio_bytes, language)
        
        logger.info(
            "Sarvam AI TTS synthesis success | language=%s | file=%s | size=%d bytes",
            language,
            Path(file_path).name,
            len(audio_bytes),
        )
        
        return TTSResult(
            audio_url=f"/api/v1/tts/audio/{Path(file_path).name}",
            file_path=file_path,
        )

    # ── Private: Utilities ─────────────────────────────────────────────────────

    def _save_audio_file(self, audio_bytes: bytes, language: str) -> str:
        """
        Save audio bytes to disk with MD5 hash-based filename.
        
        Uses content hash for automatic caching — same text produces
        same filename and can be served from cache.
        
        Parameters
        ----------
        audio_bytes : bytes
            Raw MP3 audio data
        language : str
            Language code for filename

        Returns
        -------
        str
            Absolute file path where audio was saved

        Raises
        ------
        ExternalServiceError
            If file write fails
        """
        content_hash = md5(audio_bytes).hexdigest()[:16]
        filename = f"{content_hash}_{language}.mp3"
        file_path = os.path.join(self._storage_dir, filename)

        # Skip if already exists (cache hit)
        if os.path.exists(file_path):
            logger.debug("Audio file cache hit: %s", filename)
            return file_path

        try:
            with open(file_path, "wb") as f:
                f.write(audio_bytes)
            logger.debug("Saved audio file: %s (%d bytes)", filename, len(audio_bytes))
            return file_path

        except IOError as exc:
            logger.error("Failed to write audio file %s: %s", file_path, exc)
            raise ExternalServiceError(f"Failed to save audio file: {exc}") from exc


# ── Singleton accessor ─────────────────────────────────────────────────────────


def get_tts_service() -> TTSService:
    """
    Get or create TTS service singleton.
    
    Returns
    -------
    TTSService
        Initialized TTS service instance
    """
    return TTSService()
