"""
Integration tests for /api/v1/predict and /api/v1/history/* endpoints.
ML services are replaced with deterministic mocks so no GPU/API key needed.
"""

from __future__ import annotations

import io
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from PIL import Image

from app.services.disease_model_service import DiseaseDetectionResult
from app.services.fallback_service import FallbackPrediction
from app.services.llm_service import LLMResult
from app.services.plant_validator_service import PlantValidationResult


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_jpeg_bytes() -> bytes:
    img = Image.new("RGB", (50, 50), color=(60, 180, 80))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _plant_validator_stub(is_plant: bool, conf: float = 0.95):
    svc = MagicMock()
    svc.validate = AsyncMock(
        return_value=PlantValidationResult(
            is_plant=is_plant, confidence=conf, message="stub"
        )
    )
    return svc


def _disease_stub(confidence: float = 0.92):
    svc = MagicMock()
    svc.detect = AsyncMock(
        return_value=DiseaseDetectionResult(
            plant_name="Tomato",
            disease_name="Early Blight",
            confidence_score=confidence,
        )
    )
    return svc


def _fallback_stub():
    svc = MagicMock()
    svc.predict = AsyncMock(
        return_value=FallbackPrediction(
            plant_name="Tomato",
            disease_name="Late Blight",
            confidence_score=0.85,
        )
    )
    return svc


def _llm_stub():
    svc = MagicMock()
    svc.generate_precautions = AsyncMock(
        return_value=LLMResult(
            precautions_text="Spray with copper-based fungicide.",
            audio_url=None,
        )
    )
    return svc


# ── POST /predict ─────────────────────────────────────────────────────────────


class TestPredictEndpoint:
    @patch("app.api.predict.plant_validator_service")
    @patch("app.api.predict.disease_model_service")
    @patch("app.api.predict.fallback_service")
    @patch("app.api.predict.llm_service")
    @patch("app.services.image_service.aiofiles.open")
    async def test_successful_prediction(
        self,
        mock_open,
        mock_llm,
        mock_fallback,
        mock_disease,
        mock_validator,
        client: AsyncClient,
        auth_headers: dict,
        test_user,
    ):
        # Wire stubs
        mock_validator.validate = AsyncMock(
            return_value=PlantValidationResult(is_plant=True, confidence=0.95, message="ok")
        )
        mock_disease.detect = AsyncMock(
            return_value=DiseaseDetectionResult(
                plant_name="Tomato", disease_name="Early Blight", confidence_score=0.92
            )
        )
        mock_llm.generate_precautions = AsyncMock(
            return_value=LLMResult(
                precautions_text="Apply fungicide.", audio_url=None
            )
        )
        # Mock file write
        mock_file = AsyncMock()
        mock_open.return_value.__aenter__ = AsyncMock(return_value=mock_file)
        mock_open.return_value.__aexit__ = AsyncMock(return_value=False)

        jpeg_bytes = _make_jpeg_bytes()
        resp = await client.post(
            "/api/v1/predict",
            files={"file": ("plant.jpg", jpeg_bytes, "image/jpeg")},
            data={"language": "en"},
            headers=auth_headers,
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert data["is_plant"] is True
        assert data["plant_name"] == "Tomato"
        assert data["disease_name"] == "Early Blight"
        assert data["confidence_score"] == 0.92
        assert data["fallback_used"] is False
        assert "precautions" in data
        assert "upload_id" in data
        assert "prediction_id" in data

    @patch("app.api.predict.plant_validator_service")
    @patch("app.services.image_service.aiofiles.open")
    async def test_non_plant_returns_422(
        self,
        mock_open,
        mock_validator,
        client: AsyncClient,
        auth_headers: dict,
        test_user,
    ):
        mock_validator.validate = AsyncMock(
            return_value=PlantValidationResult(is_plant=False, confidence=0.05, message="no")
        )
        mock_file = AsyncMock()
        mock_open.return_value.__aenter__ = AsyncMock(return_value=mock_file)
        mock_open.return_value.__aexit__ = AsyncMock(return_value=False)

        jpeg_bytes = _make_jpeg_bytes()
        resp = await client.post(
            "/api/v1/predict",
            files={"file": ("not_plant.jpg", jpeg_bytes, "image/jpeg")},
            data={"language": "en"},
            headers=auth_headers,
        )

        assert resp.status_code == 422
        assert resp.json()["success"] is False

    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        jpeg_bytes = _make_jpeg_bytes()
        resp = await client.post(
            "/api/v1/predict",
            files={"file": ("plant.jpg", jpeg_bytes, "image/jpeg")},
        )
        assert resp.status_code == 401

    async def test_wrong_file_type_returns_415(
        self, client: AsyncClient, auth_headers: dict, test_user
    ):
        resp = await client.post(
            "/api/v1/predict",
            files={"file": ("file.gif", b"GIF89a...", "image/gif")},
            data={"language": "en"},
            headers=auth_headers,
        )
        assert resp.status_code == 415

    async def test_missing_file_returns_422(
        self, client: AsyncClient, auth_headers: dict, test_user
    ):
        resp = await client.post(
            "/api/v1/predict",
            data={"language": "en"},
            headers=auth_headers,
        )
        assert resp.status_code == 422


# ── GET /history ──────────────────────────────────────────────────────────────


class TestHistoryEndpoint:
    async def test_empty_history(
        self, client: AsyncClient, auth_headers: dict, test_user
    ):
        resp = await client.get("/api/v1/history", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["items"] == []
        assert body["data"]["total"] == 0

    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        resp = await client.get("/api/v1/history")
        assert resp.status_code == 401

    async def test_pagination_defaults(
        self, client: AsyncClient, auth_headers: dict, test_user
    ):
        resp = await client.get(
            "/api/v1/history?page=1&page_size=10", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["page"] == 1
        assert data["page_size"] == 10

    async def test_invalid_page_returns_422(
        self, client: AsyncClient, auth_headers: dict, test_user
    ):
        resp = await client.get(
            "/api/v1/history?page=0", headers=auth_headers
        )
        assert resp.status_code == 422

    async def test_page_size_over_limit_returns_422(
        self, client: AsyncClient, auth_headers: dict, test_user
    ):
        resp = await client.get(
            "/api/v1/history?page_size=200", headers=auth_headers
        )
        assert resp.status_code == 422


# ── GET /prediction/{id} ──────────────────────────────────────────────────────


class TestGetPredictionEndpoint:
    async def test_nonexistent_prediction_returns_404(
        self, client: AsyncClient, auth_headers: dict, test_user
    ):
        fake_id = str(uuid.uuid4())
        resp = await client.get(
            f"/api/v1/prediction/{fake_id}", headers=auth_headers
        )
        assert resp.status_code == 404
        assert resp.json()["success"] is False

    async def test_invalid_uuid_returns_422(
        self, client: AsyncClient, auth_headers: dict, test_user
    ):
        resp = await client.get(
            "/api/v1/prediction/not-a-uuid", headers=auth_headers
        )
        assert resp.status_code == 422

    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        resp = await client.get(f"/api/v1/prediction/{uuid.uuid4()}")
        assert resp.status_code == 401


# ── GET /health ───────────────────────────────────────────────────────────────


class TestHealthEndpoint:
    async def test_health_check_returns_ok(self, client: AsyncClient):
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        assert resp.json()["data"]["status"] == "ok"
