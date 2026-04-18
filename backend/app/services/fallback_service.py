"""
Gemini Flash Fallback Service.

Called when the on-device disease model returns low confidence or fails.
Uses the Gemini 1.5 Flash multimodal API to analyse the plant image directly.

All HTTP communication is async via httpx to avoid blocking the event loop.
"""

from __future__ import annotations

import base64
import json
import logging
import re
from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.core.exceptions import GeminiAPIError

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=5.0)

_SYSTEM_PROMPT = (
    "You are an expert agronomist and plant pathologist. "
    "Analyse the provided plant image and identify:\n"
    "1. The plant species\n"
    "2. Any visible disease, pest damage, or nutritional deficiency\n"
    "3. Your confidence level as a percentage (0-100)\n\n"
    "Respond ONLY in the following JSON format, with no additional text:\n"
    '{"plant_name": "...", "disease_name": "...", "confidence": 85}\n'
    'Use "Healthy" for disease_name if the plant appears disease-free.'
)


# ── Data contract ─────────────────────────────────────────────────────────────


@dataclass
class FallbackPrediction:
    plant_name: str
    disease_name: str
    confidence_score: float   # 0.0 – 1.0


# ── Service ───────────────────────────────────────────────────────────────────


class FallbackService:
    """
    Wraps the Gemini 1.5 Flash API for multimodal plant-disease inference.
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
        self._model_candidates = self._build_model_candidates(model)

    # ── Public API ─────────────────────────────────────────────────────────────

    async def predict(self, image_bytes: bytes) -> FallbackPrediction:
        """
        Send *image_bytes* to Gemini Flash and parse the disease prediction.

        Raises
        ------
        GeminiAPIError
            On network errors, non-200 responses, or unparseable replies.
        """
        if not self._api_key:
            raise GeminiAPIError(
                "GEMINI_API_KEY is not configured — cannot use fallback"
            )

        payload = self._build_payload(image_bytes)
        raw_response = await self._call_api(payload)
        return self._parse_response(raw_response)

    # ── Private helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _build_payload(image_bytes: bytes) -> dict:
        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        return {
            "system_instruction": {"parts": [{"text": _SYSTEM_PROMPT}]},
            "contents": [
                {
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": b64_image,
                            }
                        },
                        {
                            "text": (
                                "Identify the plant and any disease present "
                                "in this image. Respond only in the specified JSON format."
                            )
                        },
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "topP": 0.9,
                "maxOutputTokens": 256,
            },
        }

    @staticmethod
    def _build_model_candidates(configured_model: str) -> list[str]:
        """Return unique model IDs to try, prioritizing configured value first."""
        fallbacks = [
            configured_model,
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-1.5-flash-8b",
        ]
        # Accept both "models/foo" and "foo" forms from config.
        normalized: list[str] = []
        seen: set[str] = set()
        for model in fallbacks:
            candidate = model.removeprefix("models/").strip()
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            normalized.append(candidate)
        return normalized

    async def _call_api(self, payload: dict) -> dict:
        last_http_error: httpx.HTTPStatusError | None = None
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                for model_name in self._model_candidates:
                    url = (
                        f"{self._api_url}/{model_name}"
                        f":generateContent?key={self._api_key}"
                    )
                    try:
                        response = await client.post(url, json=payload)
                        response.raise_for_status()
                        if model_name != self._model:
                            logger.warning(
                                "Gemini fallback switched model from '%s' to '%s'",
                                self._model,
                                model_name,
                            )
                        return response.json()
                    except httpx.HTTPStatusError as exc:
                        # 404 means this model ID is unavailable for current API.
                        if exc.response.status_code == 404:
                            last_http_error = exc
                            logger.warning(
                                "Gemini model '%s' not found (404), trying next candidate",
                                model_name,
                            )
                            continue
                        raise GeminiAPIError(
                            f"Gemini API returned HTTP {exc.response.status_code}: "
                            f"{exc.response.text}"
                        ) from exc

            if last_http_error is not None:
                raise GeminiAPIError(
                    "No configured Gemini model could be used for generateContent. "
                    "Update GEMINI_MODEL to a currently supported model."
                ) from last_http_error

            raise GeminiAPIError("No Gemini model candidates available")
        except httpx.TimeoutException as exc:
            raise GeminiAPIError("Gemini API request timed out") from exc
        except httpx.RequestError as exc:
            raise GeminiAPIError(
                f"Network error calling Gemini API: {exc}"
            ) from exc

    @staticmethod
    def _parse_response(raw: dict) -> FallbackPrediction:
        try:
            parts = raw["candidates"][0]["content"]["parts"]
            text_chunks = [part.get("text", "") for part in parts if isinstance(part, dict)]
            text = "\n".join(chunk for chunk in text_chunks if chunk).strip()

            # Handle markdown code fences and responses with extra prose.
            if text.startswith("```"):
                text = re.sub(r"^```(?:json)?", "", text).strip()
                text = re.sub(r"```$", "", text).strip()

            if not text.startswith("{"):
                json_match = re.search(r"\{[\s\S]*\}", text)
                if json_match:
                    text = json_match.group(0)

            data = json.loads(text)
            confidence_raw = data.get("confidence", 0)
            confidence = float(confidence_raw)
            if confidence > 1.0:
                confidence = confidence / 100.0

            return FallbackPrediction(
                plant_name=str(data["plant_name"]),
                disease_name=str(data["disease_name"]),
                confidence_score=max(0.0, min(1.0, confidence)),
            )
        except (KeyError, IndexError, json.JSONDecodeError, ValueError) as exc:
            logger.error("Failed to parse Gemini response: %s | raw=%s", exc, raw)
            raise GeminiAPIError(
                f"Could not parse Gemini response: {exc}"
            ) from exc
