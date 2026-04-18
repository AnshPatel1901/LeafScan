"""
Prediction Service — orchestrates the full disease-detection pipeline.

Flow:
    upload image
        → validate plant
            → if not plant: raise NotAPlantError
        → run CNN disease model
            → if confidence < threshold OR model failure: Gemini fallback
        → generate LLM precautions (multilingual)
        → persist everything to DB
        → return structured response
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    AppException,
    GeminiAPIError,
    NotAPlantError,
    PredictionError,
)
from app.repositories.ai_response_repository import AIResponseRepository
from app.repositories.prediction_repository import PredictionRepository
from app.repositories.upload_repository import UploadRepository
from app.schemas.prediction import PredictResponse
from app.services.disease_model_service import DiseaseModelService
from app.services.fallback_service import FallbackService
from app.services.llm_service import LLMService
from app.services.plant_validator_service import PlantValidatorService

logger = logging.getLogger(__name__)


class PredictionService:
    """
    Coordinates all sub-services to produce a final disease prediction.
    Designed for dependency injection — every collaborator is injected.
    """

    def __init__(
        self,
        db: AsyncSession,
        plant_validator: PlantValidatorService,
        disease_model: DiseaseModelService,
        fallback_svc: FallbackService,
        llm_svc: LLMService,
    ) -> None:
        self._db = db
        self._plant_validator = plant_validator
        self._disease_model = disease_model
        self._fallback_svc = fallback_svc
        self._llm_svc = llm_svc

        self._upload_repo = UploadRepository(db)
        self._prediction_repo = PredictionRepository(db)
        self._ai_response_repo = AIResponseRepository(db)

    # ── Public API ─────────────────────────────────────────────────────────────

    async def run(
        self,
        user_id: UUID,
        image_bytes: bytes,
        image_url: str,
        language: str = "en",
    ) -> PredictResponse:
        """
        Execute the full prediction pipeline.

        Parameters
        ----------
        user_id:
            UUID of the authenticated user.
        image_bytes:
            Raw image content (already validated by ImageService).
        image_url:
            Relative path stored in the DB (returned by ImageService).
        language:
            ISO 639-1 code for the LLM response language.

        Raises
        ------
        NotAPlantError
            When the plant validator is confident the image is not a plant.
        PredictionError
            When both the CNN model and Gemini fallback fail.
        """
        try:
            # ── 1. Persist upload record ──────────────────────────────────────
            upload = await self._upload_repo.create(
                user_id=user_id, image_url=image_url
            )
            logger.info("Upload created: id=%s user=%s", upload.id, user_id)

            # ── 2. Plant validation ───────────────────────────────────────────
            validation = await self._plant_validator.validate(image_bytes)
            logger.info(
                "Plant validation: is_plant=%s confidence=%.2f",
                validation.is_plant,
                validation.confidence,
            )

            if not validation.is_plant:
                # Persist a non-plant prediction record before raising
                await self._prediction_repo.create(
                    upload_id=upload.id,
                    is_plant=False,
                )
                raise NotAPlantError(
                    f"The uploaded image does not appear to be a plant "
                    f"(confidence={validation.confidence:.0%}). "
                    f"Please upload a clear photo of a plant."
                )

            # ── 3. Disease detection (CNN model) ──────────────────────────────
            plant_name: str
            disease_name: str
            confidence_score: float
            fallback_used: bool = False

            cnn_result = await self._disease_model.detect(image_bytes)

            if cnn_result and cnn_result.confidence_score >= settings.CONFIDENCE_THRESHOLD:
                plant_name = cnn_result.plant_name
                disease_name = cnn_result.disease_name
                confidence_score = cnn_result.confidence_score
                logger.info(
                    "CNN model prediction: %s / %s (confidence=%.2f)",
                    plant_name,
                    disease_name,
                    confidence_score,
                )
            else:
                # ── 4. Gemini fallback ────────────────────────────────────────
                logger.info(
                    "CNN confidence below threshold (%.2f < %.2f) — using Gemini fallback",
                    cnn_result.confidence_score if cnn_result else 0.0,
                    settings.CONFIDENCE_THRESHOLD,
                )
                fallback_used = True
                try:
                    fallback_result = await self._fallback_svc.predict(image_bytes)
                    plant_name = fallback_result.plant_name
                    disease_name = fallback_result.disease_name
                    confidence_score = fallback_result.confidence_score
                    logger.info(
                        "Gemini fallback prediction: %s / %s (confidence=%.2f)",
                        plant_name,
                        disease_name,
                        confidence_score,
                    )
                except GeminiAPIError as exc:
                    if cnn_result is not None:
                        logger.warning(
                            "Gemini fallback failed (%s); using low-confidence CNN result instead",
                            exc,
                        )
                        plant_name = cnn_result.plant_name
                        disease_name = cnn_result.disease_name
                        confidence_score = cnn_result.confidence_score
                    else:
                        logger.error("Gemini fallback also failed: %s", exc)
                        raise PredictionError(
                            "Both the CNN model and the Gemini fallback failed to "
                            "produce a prediction. Please try again later.",
                            detail=str(exc),
                        ) from exc

            # ── 5. Persist prediction ─────────────────────────────────────────
            prediction = await self._prediction_repo.create(
                upload_id=upload.id,
                is_plant=True,
                plant_name=plant_name,
                disease_name=disease_name,
                confidence_score=confidence_score,
                fallback_used=fallback_used,
            )
            logger.info("Prediction created: id=%s", prediction.id)

            # ── 6. Generate LLM precautions ───────────────────────────────────
            llm_result = await self._llm_svc.generate_precautions(
                plant_name=plant_name,
                disease_name=disease_name,
                language=language,
            )

            # ── 6b. Optional RAG enrichment ──────────────────────────────────
            rag_answer: Optional[str] = None
            rag_sources: list[str] = []
            rag_documents: list[dict] = []

            if settings.RAG_ENABLED:
                try:
                    rag_question = self._build_rag_question(
                        plant_name=plant_name,
                        disease_name=disease_name,
                    )
                    rag = self._get_rag_pipeline()
                    rag_result = await rag.query(rag_question, language=language)

                    rag_answer = rag_result.answer.strip() if rag_result.answer else None
                    rag_sources = rag_result.sources[:5]
                    rag_documents = [
                        {
                            "source": doc.source,
                            "page": doc.page,
                            "score": round(doc.score, 3) if doc.score is not None else None,
                            "preview": (
                                doc.content[:220] + "..."
                                if len(doc.content) > 220
                                else doc.content
                            ),
                        }
                        for doc in rag_result.documents[:3]
                    ]
                    logger.info(
                        "RAG enrichment complete | sources=%d docs=%d",
                        len(rag_sources),
                        len(rag_documents),
                    )
                except Exception as exc:
                    logger.warning("RAG enrichment failed (%s); continuing without RAG", exc)

            # ── 7. Persist AI response ────────────────────────────────────────
            await self._ai_response_repo.create(
                prediction_id=prediction.id,
                language=language,
                precautions_text=llm_result.precautions_text,
                audio_url=llm_result.audio_url,
            )

            # ── 8. Return structured response ─────────────────────────────────
            return PredictResponse(
                upload_id=upload.id,
                prediction_id=prediction.id,
                is_plant=True,
                plant_name=plant_name,
                disease_name=disease_name,
                confidence_score=round(confidence_score, 4),
                fallback_used=fallback_used,
                precautions=llm_result.precautions_text,
                language=language,
                audio_url=llm_result.audio_url,
                rag_answer=rag_answer,
                rag_sources=rag_sources,
                rag_documents=rag_documents,
            )
        except AppException:
            raise
        except SQLAlchemyError as exc:
            logger.exception("Database failure in prediction pipeline: %s", exc)
            await self._db.rollback()
            raise PredictionError(
                "Prediction could not be saved due to a database error.",
                detail="database_failure",
            ) from exc
        except Exception as exc:
            logger.exception("Unexpected failure in prediction pipeline: %s", exc)
            await self._db.rollback()
            raise PredictionError(
                "Prediction pipeline failed unexpectedly.",
                detail="internal_pipeline_error",
            ) from exc

    @staticmethod
    def _get_rag_pipeline():
        # Local import keeps the base prediction path lightweight when RAG is disabled.
        from app.rag.pipeline import get_rag_pipeline

        return get_rag_pipeline()

    @staticmethod
    def _build_rag_question(plant_name: str, disease_name: str) -> str:
        if disease_name.lower() == "healthy":
            return (
                f"{plant_name} crop appears healthy. "
                "Share evidence-based care and prevention practices for keeping it healthy."
            )

        return (
            f"{plant_name} has {disease_name}. "
            "Provide practical disease overview, major symptoms, immediate treatment steps, "
            "and prevention guidance for farmers."
        )
