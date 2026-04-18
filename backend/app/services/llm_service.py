"""
LLM Service — generates disease explanation and precautions.

Uses Gemini Flash as the LLM backend. Multilingual output is achieved
by injecting the target language code into the prompt.
TTS integration with Google Cloud TTS and Servaai for audio generation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import httpx

from app.core.config import settings
from app.core.exceptions import ExternalServiceError
from app.services.tts_service import get_tts_service

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(connect=10.0, read=90.0, write=10.0, pool=5.0)

# ISO 639-1 → full language name for the prompt
# Extended support for more languages
_LANGUAGE_NAMES: dict[str, str] = {
    "en": "English",
    "hi": "Hindi",
    "ta": "Tamil",
    "te": "Telugu",
    "mr": "Marathi",
    "bn": "Bengali",
    "gu": "Gujarati",
    "kn": "Kannada",
    "ml": "Malayalam",
    "pa": "Punjabi",
    "fr": "French",
    "es": "Spanish",
    "de": "German",
    "zh": "Chinese (Simplified)",
    "ar": "Arabic",
    "pt": "Portuguese",
    "it": "Italian",
    "ja": "Japanese",
    "ko": "Korean",
}


# ── Data contract ─────────────────────────────────────────────────────────────


@dataclass
class LLMResult:
    """Result of LLM generation with optional TTS output."""
    precautions_text: str
    audio_url: Optional[str] = None


# ── Service ───────────────────────────────────────────────────────────────────


class LLMService:
    """
    Generates agronomic explanations and precautions for detected diseases.

    Features:
        • Multilingual: ISO 639-1 language codes
        • TTS Integration: Google Cloud TTS & Servaai support
        • Fallback: Static text if LLM unavailable
        • Error Handling: Comprehensive logging and error recovery
    """

    def __init__(
        self,
        api_key: str = settings.GEMINI_API_KEY,
        model: str = settings.GEMINI_MODEL,
        api_url: str = settings.GEMINI_API_URL,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._api_url = api_url
        self._tts_service = get_tts_service()

    # ── Public API ─────────────────────────────────────────────────────────────

    async def generate_precautions(
        self,
        plant_name: str,
        disease_name: str,
        language: str = "en",
    ) -> LLMResult:
        """
        Generate disease explanation and precautions in *language*.

        Parameters
        ----------
        plant_name : str
            Name of the plant (e.g., "Tomato", "Potato")
        disease_name : str
            Name of the detected disease
        language : str
            ISO 639-1 language code (default: "en")

        Returns
        -------
        LLMResult
            Precautions text and optional audio URL

        Notes
        -----
        Falls back to static message if LLM fails.
        Optionally generates audio if TTS_ENABLED in config.
        """
        try:
            text = await self._call_llm(plant_name, disease_name, language)
            logger.info(
                "LLM generation success | plant=%s disease=%s lang=%s | text_len=%d",
                plant_name, disease_name, language, len(text)
            )
        except Exception as exc:
            logger.warning(
                "LLM generation failed (%s); using fallback text", exc
            )
            text = self._static_fallback(plant_name, disease_name)

        # Generate TTS audio if enabled
        audio_url = None
        if settings.TTS_ENABLED:
            try:
                tts_result = await self._tts_service.synthesize(text, language)
                if tts_result:
                    audio_url = tts_result.audio_url
                    logger.info("TTS generated successfully | lang=%s | url=%s", language, audio_url)
            except Exception as exc:
                logger.warning("TTS generation failed (%s); continuing without audio", exc)

        return LLMResult(precautions_text=text, audio_url=audio_url)

    # ── Public utilities ───────────────────────────────────────────────────────

    @staticmethod
    def get_supported_languages() -> list[str]:
        """Return list of supported language codes."""
        return list(_LANGUAGE_NAMES.keys())

    @staticmethod
    def is_language_supported(language: str) -> bool:
        """Check if language is supported."""
        return language in _LANGUAGE_NAMES

    # ── Private helpers ────────────────────────────────────────────────────────

    def _build_prompt(
        self, plant_name: str, disease_name: str, language: str
    ) -> str:
        """Build LLM prompt with language-specific instructions."""
        lang_name = _LANGUAGE_NAMES.get(language, "English")
        
        if disease_name.lower() == "healthy":
            return (
                f"The {plant_name} plant appears healthy. "
                f"In {lang_name}, provide 3-4 sentences of general tips "
                f"to keep this plant healthy and disease-free. "
                f"Focus on practical, actionable advice for farmers."
            )
        
        return (
            f"A {plant_name} plant has been diagnosed with '{disease_name}'. "
            f"Respond ONLY in {lang_name}. "
            f"Do not use any other language.\n\n"
            f"Structure your response exactly as follows:\n\n"
            f"**About the disease:** (2-3 sentences explaining what it is and impact)\n\n"
            f"**Symptoms to watch:** (bullet list of 3-4 visual symptoms)\n\n"
            f"**Immediate actions:** (bullet list of 3-4 urgent steps to take)\n\n"
            f"**Prevention:** (bullet list of 3-4 preventive measures)\n\n"
            f"Keep the response practical, concise, and suitable for farmers. "
            f"Use simple language."
        )

    async def _call_llm(
        self, plant_name: str, disease_name: str, language: str
    ) -> str:
        """Call Gemini API to generate precautions."""
        if not self._api_key:
            raise ExternalServiceError("GEMINI_API_KEY not configured")

        prompt = self._build_prompt(plant_name, disease_name, language)
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.4,
                "topP": 0.95,
                "maxOutputTokens": 1024,
            },
        }
        url = (
            f"{self._api_url}/{self._model}"
            f":generateContent?key={self._api_key}"
        )
        
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()

            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except httpx.HTTPError as exc:
            raise ExternalServiceError(f"Gemini API error: {exc}") from exc
        except (KeyError, IndexError) as exc:
            raise ExternalServiceError(
                f"Unexpected Gemini response structure: {exc}"
            ) from exc

    @staticmethod
    def _static_fallback(plant_name: str, disease_name: str) -> str:
        """Return a practical offline advisory when the LLM is unavailable."""
        disease = disease_name.strip()
        disease_lower = disease.lower()

        if disease_lower == "healthy":
            return (
                f"Your {plant_name} plant looks healthy.\n\n"
                "**General care tips:**\n"
                "- Keep leaves dry by watering at the base early in the day.\n"
                "- Maintain proper spacing and airflow to reduce fungal pressure.\n"
                "- Scout the plant 2-3 times per week to catch early symptoms.\n"
                "- Use clean tools and remove heavily damaged leaves promptly."
            )

        return (
            f"Disease detected: **{disease}** on {plant_name}.\n\n"
            "**Immediate actions:**\n"
            "- Isolate affected plants/leaves to prevent spread to others.\n"
            "- Remove visibly infected tissue and dispose safely away from fields.\n"
            "- Avoid overhead irrigation; keep foliage as dry as possible.\n"
            "- Consult a local agronomist for crop-approved treatment options."
        )

