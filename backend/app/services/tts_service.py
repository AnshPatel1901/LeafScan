"""
Text-to-Speech (TTS) Service — converts text to audio using Google Cloud TTS or Servaai.

Supports:
    • Google Cloud Text-to-Speech API
    • Servaai TTS API
    
Environment variables required:
    • GOOGLE_TTS_API_KEY (for Google TTS)
    • SERVAAI_API_KEY (for Servaai TTS)
    • TTS_PROVIDER (google or servaai)
"""

from __future__ import annotations

import base64
import io
import logging
import mimetypes
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from hashlib import md5

import httpx

from app.core.config import settings
from app.core.exceptions import ExternalServiceError

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(connect=10.0, read=90.0, write=10.0, pool=5.0)

# Language code mapping for TTS providers
_LANGUAGE_CODE_MAP: dict[str, dict[str, str]] = {
    "en": {"google": "en-US", "servaai": "en-US"},
    "hi": {"google": "hi-IN", "servaai": "hi-IN"},
    "ta": {"google": "ta-IN", "servaai": "ta-IN"},
    "te": {"google": "te-IN", "servaai": "te-IN"},
    "mr": {"google": "mr-IN", "servaai": "mr-IN"},
    "bn": {"google": "bn-IN", "servaai": "bn-IN"},
    "gu": {"google": "gu-IN", "servaai": "gu-IN"},
    "kn": {"google": "kn-IN", "servaai": "kn-IN"},
    "ml": {"google": "ml-IN", "servaai": "ml-IN"},
    "pa": {"google": "pa-IN", "servaai": "pa-IN"},
    "fr": {"google": "fr-FR", "servaai": "fr-FR"},
    "es": {"google": "es-ES", "servaai": "es-ES"},
    "de": {"google": "de-DE", "servaai": "de-DE"},
    "zh": {"google": "zh-CN", "servaai": "zh-CN"},
    "ar": {"google": "ar-SA", "servaai": "ar-SA"},
    "pt": {"google": "pt-BR", "servaai": "pt-BR"},
    "it": {"google": "it-IT", "servaai": "it-IT"},
    "ja": {"google": "ja-JP", "servaai": "ja-JP"},
    "ko": {"google": "ko-KR", "servaai": "ko-KR"},
}


@dataclass
class TTSResult:
    """Result of TTS operation."""
    audio_url: str
    duration_seconds: Optional[float] = None
    file_path: Optional[str] = None


class TTSService:
    """
    Text-to-Speech service supporting multiple providers.
    
    Converts text to audio files and stores them locally.
    Returns a relative URL for streaming or access.
    """

    def __init__(
        self,
        tts_enabled: bool = settings.TTS_ENABLED,
        provider: str = settings.TTS_PROVIDER,
        storage_dir: str = settings.TTS_STORAGE_DIR,
    ) -> None:
        self._enabled = tts_enabled
        self._provider = provider
        self._storage_dir = storage_dir
        
        # Create storage directory if needed
        if self._enabled:
            Path(self._storage_dir).mkdir(parents=True, exist_ok=True)
            logger.info("TTS service initialized with provider='%s'", provider)

    # ── Public API ─────────────────────────────────────────────────────────────

    async def synthesize(
        self,
        text: str,
        language: str = "en",
    ) -> Optional[TTSResult]:
        """
        Convert text to speech in the specified language.

        Parameters
        ----------
        text : str
            Text to convert to speech (max 5000 characters recommended)
        language : str
            Language code (e.g., 'en', 'hi', 'ta')

        Returns
        -------
        Optional[TTSResult]
            TTS result with audio URL, or None if TTS is disabled/fails

        Raises
        ------
        ExternalServiceError
            If TTS API call fails or provider is misconfigured
        ValueError
            If language is not supported
        """
        if not self._enabled:
            logger.debug("TTS is disabled in config")
            return None

        if not text or not text.strip():
            logger.warning("Received empty text for TTS")
            return None

        # Validate language
        if language not in _LANGUAGE_CODE_MAP:
            logger.warning("Unsupported language for TTS: %s", language)
            return None

        # Truncate very long text (APIs have limits)
        if len(text) > 5000:
            logger.warning("Text too long for TTS (%d chars), truncating", len(text))
            text = text[:5000]

        try:
            if self._provider == "google":
                return await self._synthesize_google(text, language)
            elif self._provider == "servaai":
                return await self._synthesize_servaai(text, language)
            else:
                raise ExternalServiceError(f"Unknown TTS provider: {self._provider}")
        except ExternalServiceError:
            raise
        except Exception as exc:
            logger.exception("Unexpected error in TTS synthesis")
            raise ExternalServiceError("TTS synthesis failed") from exc

    # ── Private: Google TTS ────────────────────────────────────────────────────

    async def _synthesize_google(self, text: str, language: str) -> TTSResult:
        """
        Google Cloud Text-to-Speech synthesis.
        
        Requires GOOGLE_TTS_API_KEY environment variable.
        """
        api_key = settings.GOOGLE_TTS_API_KEY
        if not api_key:
            raise ExternalServiceError("GOOGLE_TTS_API_KEY not configured")

        lang_code = _LANGUAGE_CODE_MAP[language]["google"]
        url = (
            f"https://texttospeech.googleapis.com/v1/text:synthesize"
            f"?key={api_key}"
        )

        payload = {
            "input": {"text": text},
            "voice": {
                "languageCode": lang_code,
                "ssmlGender": "NEUTRAL",
            },
            "audioConfig": {
                "audioEncoding": "MP3",
                "pitch": 0.0,
                "speakingRate": 1.0,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()

            # Extract and decode audio
            audio_content = data.get("audioContent")
            if not audio_content:
                raise ExternalServiceError("No audio content in Google TTS response")

            # Save audio file
            audio_bytes = base64.b64decode(audio_content)
            file_path = self._save_audio_file(audio_bytes, language)

            logger.info("Google TTS success: %s", file_path)
            return TTSResult(
                audio_url=f"/api/tts/audio/{Path(file_path).name}",
                file_path=file_path,
            )

        except httpx.HTTPError as exc:
            logger.exception("Google TTS API error")
            raise ExternalServiceError("Google TTS API failed") from exc

    # ── Private: Servaai TTS ───────────────────────────────────────────────────

    async def _synthesize_servaai(self, text: str, language: str) -> TTSResult:
        """
        Servaai Text-to-Speech synthesis.
        
        Requires SERVAAI_API_KEY environment variable.
        """
        api_key = settings.SERVAAI_API_KEY
        if not api_key:
            raise ExternalServiceError("SERVAAI_API_KEY not configured")

        lang_code = _LANGUAGE_CODE_MAP[language]["servaai"]
        url = "https://api.servaai.com/v1/synthesis"

        payload = {
            "text": text,
            "language": lang_code,
            "voice_id": settings.SERVAAI_VOICE_ID,
            "format": "mp3",
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                audio_bytes = resp.content

            # Save audio file
            file_path = self._save_audio_file(audio_bytes, language)

            logger.info("Servaai TTS success: %s", file_path)
            return TTSResult(
                audio_url=f"/api/tts/audio/{Path(file_path).name}",
                file_path=file_path,
            )

        except httpx.HTTPError as exc:
            logger.exception("Servaai TTS API error")
            raise ExternalServiceError("Servaai TTS API failed") from exc

    # ── Private: Utilities ─────────────────────────────────────────────────────

    def _save_audio_file(self, audio_bytes: bytes, language: str) -> str:
        """
        Save audio bytes to file and return relative path.
        
        Uses MD5 hash of content for uniqueness and caching.
        """
        content_hash = md5(audio_bytes).hexdigest()
        filename = f"{content_hash}_{language}.mp3"
        file_path = os.path.join(self._storage_dir, filename)

        # Avoid rewriting if file already exists
        if os.path.exists(file_path):
            logger.debug("Audio file already exists: %s", file_path)
            return file_path

        try:
            with open(file_path, "wb") as f:
                f.write(audio_bytes)
            logger.debug("Audio file saved: %s (%d bytes)", file_path, len(audio_bytes))
            return file_path
        except IOError as exc:
            logger.exception("Failed to save audio file")
            raise ExternalServiceError("Failed to save audio file") from exc

    @staticmethod
    def get_supported_languages() -> list[str]:
        """Return list of supported language codes."""
        return list(_LANGUAGE_CODE_MAP.keys())


# Singleton instance
_tts_service_instance: Optional[TTSService] = None


def get_tts_service() -> TTSService:
    """Get or create TTS service singleton."""
    global _tts_service_instance
    if _tts_service_instance is None:
        _tts_service_instance = TTSService()
    return _tts_service_instance
