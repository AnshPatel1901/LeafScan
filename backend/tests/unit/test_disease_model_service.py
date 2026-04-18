"""
Unit tests for DiseaseModelService.

All TensorFlow / numpy calls are mocked — no GPU or real model needed.
"""

from __future__ import annotations

import io
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from app.services.disease_model_service import (
    DiseaseDetectionResult,
    DiseaseModelService,
    _STUB_LABEL_MAP,
)


# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_jpeg_bytes(size: tuple[int, int] = (100, 100)) -> bytes:
    img = Image.new("RGB", size, color=(60, 180, 80))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _make_service(model=None, label_map=None) -> DiseaseModelService:
    """Build a DiseaseModelService with injected model + label map."""
    svc = DiseaseModelService.__new__(DiseaseModelService)
    svc._model_path = "models/disease_model.keras"
    svc._model = model
    svc._label_map = label_map if label_map is not None else _STUB_LABEL_MAP
    return svc


# ── _load_label_map ────────────────────────────────────────────────────────────


class TestLoadLabelMap:
    def test_returns_stub_when_file_missing(self, tmp_path):
        svc = DiseaseModelService.__new__(DiseaseModelService)
        svc._model_path = str(tmp_path / "model.keras")
        svc._model = None

        with patch("app.services.disease_model_service.settings") as mock_cfg:
            mock_cfg.DISEASE_MODEL_PATH = str(tmp_path / "model.keras")
            mock_cfg.DISEASE_LABEL_MAP_PATH = str(tmp_path / "nonexistent.json")
            result = svc._load_label_map()

        assert result == _STUB_LABEL_MAP

    def test_parses_valid_label_map_json(self, tmp_path):
        labels = [
            {"index": 0, "plant_name": "Tomato", "disease_name": "Early Blight"},
            {"index": 1, "plant_name": "Potato", "disease_name": "Healthy"},
        ]
        label_file = tmp_path / "label_map.json"
        label_file.write_text(json.dumps(labels), encoding="utf-8")

        svc = DiseaseModelService.__new__(DiseaseModelService)
        svc._model_path = "model.keras"
        svc._model = None

        with patch("app.services.disease_model_service.settings") as mock_cfg:
            mock_cfg.DISEASE_LABEL_MAP_PATH = str(label_file)
            result = svc._load_label_map()

        assert len(result) == 2
        assert result[0] == ("Tomato", "Early Blight")
        assert result[1] == ("Potato", "Healthy")

    def test_falls_back_to_stub_on_invalid_json(self, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not-valid-json", encoding="utf-8")

        svc = DiseaseModelService.__new__(DiseaseModelService)
        svc._model_path = "model.keras"
        svc._model = None

        with patch("app.services.disease_model_service.settings") as mock_cfg:
            mock_cfg.DISEASE_LABEL_MAP_PATH = str(bad_file)
            result = svc._load_label_map()

        assert result == _STUB_LABEL_MAP

    def test_falls_back_to_stub_on_empty_list(self, tmp_path):
        label_file = tmp_path / "empty.json"
        label_file.write_text("[]", encoding="utf-8")

        svc = DiseaseModelService.__new__(DiseaseModelService)
        svc._model_path = "model.keras"
        svc._model = None

        with patch("app.services.disease_model_service.settings") as mock_cfg:
            mock_cfg.DISEASE_LABEL_MAP_PATH = str(label_file)
            result = svc._load_label_map()

        assert result == _STUB_LABEL_MAP

    def test_sorts_by_index(self, tmp_path):
        # Provide labels out of order
        labels = [
            {"index": 2, "plant_name": "Corn", "disease_name": "Rust"},
            {"index": 0, "plant_name": "Tomato", "disease_name": "Blight"},
            {"index": 1, "plant_name": "Potato", "disease_name": "Healthy"},
        ]
        label_file = tmp_path / "label_map.json"
        label_file.write_text(json.dumps(labels), encoding="utf-8")

        svc = DiseaseModelService.__new__(DiseaseModelService)
        svc._model_path = "model.keras"
        svc._model = None

        with patch("app.services.disease_model_service.settings") as mock_cfg:
            mock_cfg.DISEASE_LABEL_MAP_PATH = str(label_file)
            result = svc._load_label_map()

        assert result[0] == ("Tomato", "Blight")
        assert result[1] == ("Potato", "Healthy")
        assert result[2] == ("Corn", "Rust")


# ── _preprocess ────────────────────────────────────────────────────────────────


class TestPreprocess:
    def test_returns_nhwc_array(self):
        import numpy as np

        svc = _make_service()
        arr = svc._preprocess(_make_jpeg_bytes())

        assert arr.shape == (1, 224, 224, 3)

    def test_values_in_zero_one_range(self):
        import numpy as np

        svc = _make_service()
        arr = svc._preprocess(_make_jpeg_bytes())

        assert float(arr.min()) >= 0.0
        assert float(arr.max()) <= 1.0

    def test_accepts_png_bytes(self):
        img = Image.new("RGB", (80, 80), color=(200, 100, 50))
        buf = io.BytesIO()
        img.save(buf, format="PNG")

        svc = _make_service()
        arr = svc._preprocess(buf.getvalue())

        assert arr.shape == (1, 224, 224, 3)


# ── _run_inference ─────────────────────────────────────────────────────────────


class TestRunInference:
    @pytest.mark.asyncio
    async def test_returns_none_when_model_is_none(self):
        svc = _make_service(model=None)
        result = await svc._run_inference(None)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_detection_result_for_top_class(self):
        import numpy as np

        # Fake model: returns probs where index 2 (Tomato/Healthy) is highest
        mock_model = MagicMock()
        num_classes = len(_STUB_LABEL_MAP)
        probs = np.zeros((1, num_classes), dtype=np.float32)
        probs[0, 2] = 0.95  # Tomato / Healthy
        mock_model.predict.return_value = probs

        svc = _make_service(model=mock_model)
        dummy_input = np.zeros((1, 224, 224, 3), dtype=np.float32)
        result = await svc._run_inference(dummy_input)

        assert result is not None
        assert result.plant_name == "Tomato"
        assert result.disease_name == "Healthy"
        assert abs(result.confidence_score - 0.95) < 1e-5

    @pytest.mark.asyncio
    async def test_returns_none_when_class_index_out_of_bounds(self):
        import numpy as np

        # Model outputs more classes than our label map
        mock_model = MagicMock()
        big_probs = np.zeros((1, 999), dtype=np.float32)
        big_probs[0, 500] = 0.99  # index 500 > len(_STUB_LABEL_MAP)
        mock_model.predict.return_value = big_probs

        svc = _make_service(model=mock_model)
        dummy_input = np.zeros((1, 224, 224, 3), dtype=np.float32)
        result = await svc._run_inference(dummy_input)

        assert result is None

    @pytest.mark.asyncio
    async def test_all_classes_dict_length_matches_label_map(self):
        import numpy as np

        num_classes = len(_STUB_LABEL_MAP)
        mock_model = MagicMock()
        probs = np.full((1, num_classes), 1.0 / num_classes, dtype=np.float32)
        mock_model.predict.return_value = probs

        svc = _make_service(model=mock_model)
        dummy_input = np.zeros((1, 224, 224, 3), dtype=np.float32)
        result = await svc._run_inference(dummy_input)

        assert result is not None
        assert len(result.all_classes) == num_classes


# ── detect (public) ────────────────────────────────────────────────────────────


class TestDetect:
    @pytest.mark.asyncio
    async def test_returns_none_when_model_not_loaded(self):
        svc = _make_service(model=None)
        result = await svc.detect(_make_jpeg_bytes())
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_result_with_real_numpy(self):
        import numpy as np

        num_classes = len(_STUB_LABEL_MAP)
        mock_model = MagicMock()
        probs = np.zeros((1, num_classes), dtype=np.float32)
        probs[0, 0] = 0.88  # Tomato / Early Blight
        mock_model.predict.return_value = probs

        svc = _make_service(model=mock_model)
        result = await svc.detect(_make_jpeg_bytes())

        assert isinstance(result, DiseaseDetectionResult)
        assert result.plant_name == "Tomato"
        assert result.disease_name == "Early Blight"
        assert abs(result.confidence_score - 0.88) < 1e-5

    @pytest.mark.asyncio
    async def test_returns_none_on_preprocessing_exception(self):
        svc = _make_service()
        # Pass invalid bytes that cannot be opened as an image
        result = await svc.detect(b"this-is-not-an-image")
        assert result is None

    @pytest.mark.asyncio
    async def test_model_version_matches_path_filename(self):
        import numpy as np

        num_classes = len(_STUB_LABEL_MAP)
        mock_model = MagicMock()
        probs = np.zeros((1, num_classes), dtype=np.float32)
        probs[0, 1] = 0.91
        mock_model.predict.return_value = probs

        svc = _make_service(model=mock_model)
        svc._model_path = "models/disease_model_v2.keras"
        result = await svc.detect(_make_jpeg_bytes())

        assert result is not None
        assert result.model_version == "disease_model_v2.keras"
