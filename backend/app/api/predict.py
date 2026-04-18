"""
Prediction endpoint — POST /predict.

Accepts a multipart image upload and returns a complete disease prediction
with LLM-generated precautions.
"""

import logging

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_current_user, get_db
from app.core.exceptions import AppException, InvalidRequestError, PredictionError
from app.models.user import User
from app.schemas.prediction import PredictResponse
from app.schemas.response import APIResponse
from app.services import (
    disease_model_service,
    fallback_service,
    llm_service,
    plant_validator_service,
)
from app.services.image_service import ImageService
from app.services.prediction_service import PredictionService

router = APIRouter(tags=["Prediction"])

_image_service = ImageService()
logger = logging.getLogger(__name__)


@router.post(
    "/predict",
    response_model=APIResponse[PredictResponse],
    status_code=status.HTTP_200_OK,
    summary="Upload a plant image and get disease prediction",
    description=(
        "Upload a JPG/PNG image of a plant. "
        "The system will validate that it contains a plant, "
        "detect any disease using the CNN model (with Gemini Flash fallback), "
        "and return disease precautions in the selected language."
    ),
)
async def predict(
    request: Request,
    file: UploadFile = File(
        ...,
        description="Plant image file (JPG or PNG, max 10 MB)",
    ),
    language: str = Form(default="en", description="ISO 639-1 language code (e.g., 'en', 'hi', 'ta')"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[PredictResponse]:
    request_id = getattr(request.state, "request_id", "unknown")
    safe_filename = (file.filename or "").strip()

    logger.info(
        "[%s] /predict start | user_id=%s | file=%s | content_type=%s",
        request_id,
        current_user.id,
        safe_filename or "<missing>",
        file.content_type,
    )

    if not safe_filename:
        raise InvalidRequestError("Missing file name in uploaded image")

    try:
        # ── 1. Validate & save image ──────────────────────────────────────────
        image_url, image_bytes = await _image_service.validate_and_save(
            file=file,
            user_id=str(current_user.id),
        )
        logger.info("[%s] Image saved: %s", request_id, image_url)

        # ── 2. Run prediction pipeline ────────────────────────────────────────
        prediction_svc = PredictionService(
            db=db,
            plant_validator=plant_validator_service,
            disease_model=disease_model_service,
            fallback_svc=fallback_service,
            llm_svc=llm_service,
        )

        result = await prediction_svc.run(
            user_id=current_user.id,
            image_bytes=image_bytes,
            image_url=image_url,
            language=language,
        )

        logger.info(
            "[%s] /predict success | upload_id=%s | prediction_id=%s",
            request_id,
            result.upload_id,
            result.prediction_id,
        )
        return APIResponse.ok(result, "Prediction completed successfully")
    except AppException:
        # Preserve domain-specific status codes and messages from services.
        logger.warning("[%s] /predict domain error", request_id, exc_info=True)
        raise
    except Exception as exc:
        logger.exception("[%s] /predict unexpected error: %s", request_id, exc)
        raise PredictionError(
            "Prediction request failed unexpectedly.",
            detail={"request_id": request_id},
        ) from exc
