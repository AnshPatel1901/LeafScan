"""
Unit tests for PredictionService — pipeline orchestration.
All collaborators (ML services, repos) are mocked.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import GeminiAPIError, NotAPlantError, PredictionError
from app.services.disease_model_service import DiseaseDetectionResult
from app.services.fallback_service import FallbackPrediction
from app.services.llm_service import LLMResult
from app.services.plant_validator_service import PlantValidationResult
from app.services.prediction_service import PredictionService


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_upload(upload_id=None):
    upload = MagicMock()
    upload.id = upload_id or uuid.uuid4()
    return upload


def _make_prediction(prediction_id=None):
    pred = MagicMock()
    pred.id = prediction_id or uuid.uuid4()
    return pred


def _build_service(
    *,
    is_plant: bool = True,
    plant_confidence: float = 0.95,
    cnn_result=None,
    fallback_result=None,
    fallback_raises=False,
    llm_text: str = "Apply fungicide.",
):
    db = AsyncMock()

    plant_validator = MagicMock()
    plant_validator.validate = AsyncMock(
        return_value=PlantValidationResult(
            is_plant=is_plant,
            confidence=plant_confidence,
            message="ok",
        )
    )

    disease_model = MagicMock()
    disease_model.detect = AsyncMock(return_value=cnn_result)

    fallback_svc = MagicMock()
    if fallback_raises:
        fallback_svc.predict = AsyncMock(
            side_effect=GeminiAPIError("API error")
        )
    else:
        fallback_svc.predict = AsyncMock(return_value=fallback_result)

    llm_svc = MagicMock()
    llm_svc.generate_precautions = AsyncMock(
        return_value=LLMResult(precautions_text=llm_text, audio_url=None)
    )

    upload = _make_upload()
    prediction = _make_prediction()

    upload_repo = AsyncMock()
    upload_repo.create = AsyncMock(return_value=upload)

    prediction_repo = AsyncMock()
    prediction_repo.create = AsyncMock(return_value=prediction)

    ai_response_repo = AsyncMock()
    ai_response_repo.create = AsyncMock(return_value=MagicMock())

    svc = PredictionService(
        db=db,
        plant_validator=plant_validator,
        disease_model=disease_model,
        fallback_svc=fallback_svc,
        llm_svc=llm_svc,
    )
    # Replace repos with mocks
    svc._upload_repo = upload_repo
    svc._prediction_repo = prediction_repo
    svc._ai_response_repo = ai_response_repo

    return svc


IMAGE_BYTES = b"\xff\xd8\xff" + b"\x00" * 100  # Fake bytes (mocked path)
USER_ID = uuid.uuid4()
IMAGE_URL = "user/abc.jpg"


# ── Not-a-plant path ──────────────────────────────────────────────────────────


class TestNotPlantPath:
    async def test_raises_not_a_plant_error(self):
        svc = _build_service(is_plant=False, plant_confidence=0.05)
        with pytest.raises(NotAPlantError):
            await svc.run(USER_ID, IMAGE_BYTES, IMAGE_URL)

    async def test_upload_record_still_created(self):
        svc = _build_service(is_plant=False, plant_confidence=0.05)
        with pytest.raises(NotAPlantError):
            await svc.run(USER_ID, IMAGE_BYTES, IMAGE_URL)
        svc._upload_repo.create.assert_awaited_once()

    async def test_non_plant_prediction_record_created(self):
        svc = _build_service(is_plant=False, plant_confidence=0.05)
        with pytest.raises(NotAPlantError):
            await svc.run(USER_ID, IMAGE_BYTES, IMAGE_URL)
        svc._prediction_repo.create.assert_awaited_once_with(
            upload_id=svc._upload_repo.create.return_value.id,
            is_plant=False,
        )


# ── CNN high-confidence path ──────────────────────────────────────────────────


class TestCNNHighConfidence:
    async def test_returns_cnn_result_no_fallback(self):
        cnn = DiseaseDetectionResult(
            plant_name="Potato",
            disease_name="Late Blight",
            confidence_score=0.91,
        )
        svc = _build_service(cnn_result=cnn)
        result = await svc.run(USER_ID, IMAGE_BYTES, IMAGE_URL)

        assert result.plant_name == "Potato"
        assert result.disease_name == "Late Blight"
        assert result.fallback_used is False

    async def test_fallback_not_called(self):
        cnn = DiseaseDetectionResult(
            plant_name="Potato",
            disease_name="Late Blight",
            confidence_score=0.91,
        )
        svc = _build_service(cnn_result=cnn)
        await svc.run(USER_ID, IMAGE_BYTES, IMAGE_URL)
        svc._fallback_svc.predict.assert_not_awaited()

    async def test_llm_called_with_correct_disease(self):
        cnn = DiseaseDetectionResult(
            plant_name="Potato",
            disease_name="Late Blight",
            confidence_score=0.91,
        )
        svc = _build_service(cnn_result=cnn)
        await svc.run(USER_ID, IMAGE_BYTES, IMAGE_URL)
        svc._llm_svc.generate_precautions.assert_awaited_once_with(
            plant_name="Potato",
            disease_name="Late Blight",
            language="en",
        )


# ── Fallback path (low confidence) ───────────────────────────────────────────


class TestFallbackPath:
    async def test_fallback_used_when_low_confidence(self):
        cnn = DiseaseDetectionResult(
            plant_name="Corn",
            disease_name="Common Rust",
            confidence_score=0.40,  # Below 0.75 threshold
        )
        fb = FallbackPrediction(
            plant_name="Corn",
            disease_name="Northern Leaf Blight",
            confidence_score=0.88,
        )
        svc = _build_service(cnn_result=cnn, fallback_result=fb)
        result = await svc.run(USER_ID, IMAGE_BYTES, IMAGE_URL)

        assert result.fallback_used is True
        assert result.disease_name == "Northern Leaf Blight"

    async def test_fallback_used_when_model_returns_none(self):
        fb = FallbackPrediction(
            plant_name="Wheat",
            disease_name="Yellow Rust",
            confidence_score=0.82,
        )
        svc = _build_service(cnn_result=None, fallback_result=fb)
        result = await svc.run(USER_ID, IMAGE_BYTES, IMAGE_URL)

        assert result.fallback_used is True
        assert result.plant_name == "Wheat"


# ── Both CNN and Gemini fail ──────────────────────────────────────────────────


class TestBothFail:
    async def test_prediction_error_raised(self):
        cnn = DiseaseDetectionResult(
            plant_name="X",
            disease_name="Y",
            confidence_score=0.10,
        )
        svc = _build_service(
            cnn_result=cnn, fallback_raises=True
        )
        with pytest.raises(PredictionError):
            await svc.run(USER_ID, IMAGE_BYTES, IMAGE_URL)


# ── Response structure ────────────────────────────────────────────────────────


class TestResponseStructure:
    async def test_full_response_fields_populated(self):
        cnn = DiseaseDetectionResult(
            plant_name="Tomato",
            disease_name="Early Blight",
            confidence_score=0.93,
        )
        svc = _build_service(cnn_result=cnn, llm_text="Use copper fungicide.")
        result = await svc.run(USER_ID, IMAGE_BYTES, IMAGE_URL, language="hi")

        assert result.upload_id is not None
        assert result.prediction_id is not None
        assert result.is_plant is True
        assert result.plant_name == "Tomato"
        assert result.disease_name == "Early Blight"
        assert result.confidence_score == 0.93
        assert result.precautions == "Use copper fungicide."
        assert result.language == "hi"
        assert result.audio_url is None
