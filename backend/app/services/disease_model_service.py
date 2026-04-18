"""
Disease Detection Model Service (stub).

─────────────────────────────────────────────────────────────────────────────
PRODUCTION NOTE
─────────────────────────────────────────────────────────────────────────────
Swap `_run_inference` with your real multi-class CNN for plant disease
classification. The public `detect` interface remains unchanged.

Typical swap:
    1. Load your SavedModel / .h5 / ONNX / TorchScript in __init__
    2. Preprocess to (224, 224, 3) and normalise to [0, 1]
    3. Run model.predict → top-1 class index + confidence
    4. Map class index → (plant_name, disease_name) via a label map JSON
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import io
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image

from app.core.config import settings

logger = logging.getLogger(__name__)

_BACKEND_ROOT = Path(__file__).resolve().parents[2]


# ── Data contracts ─────────────────────────────────────────────────────────────


@dataclass
class DiseaseDetectionResult:
    plant_name: str
    disease_name: str
    confidence_score: float     # 0.0 – 1.0
    all_classes: dict[str, float] = field(default_factory=dict)
    model_version: str = "stub-v0"


# ── Stub label map ─────────────────────────────────────────────────────────────
# Replace with a real label_map.json loaded from disk.

_STUB_LABEL_MAP: list[tuple[str, str]] = [
    ("Tomato", "Early Blight"),
    ("Tomato", "Late Blight"),
    ("Tomato", "Healthy"),
    ("Potato", "Early Blight"),
    ("Potato", "Late Blight"),
    ("Potato", "Healthy"),
    ("Corn", "Northern Leaf Blight"),
    ("Corn", "Common Rust"),
    ("Corn", "Healthy"),
    ("Wheat", "Yellow Rust"),
    ("Wheat", "Powdery Mildew"),
    ("Wheat", "Healthy"),
]


# ── Service ────────────────────────────────────────────────────────────────────


class DiseaseModelService:
    """
    Classifies plant disease from a validated plant image.

    Designed as a singleton — load once, serve many requests.
    """

    _INPUT_SIZE: tuple[int, int] = (224, 224)

    def __init__(
        self, model_path: str = settings.DISEASE_MODEL_PATH
    ) -> None:
        self._model_path = model_path
        self._model = None  # Lazy-loaded on first use
        self._model_loaded = False
        self._model_load_error = None
        self._label_map = self._load_label_map()

    # ── Public API ─────────────────────────────────────────────────────────────

    async def detect(self, image_bytes: bytes) -> DiseaseDetectionResult | None:
        """
        Run disease detection on *image_bytes*.

        Returns
        -------
        DiseaseDetectionResult or None
            None signals that the model could not produce a prediction
            (triggers the Gemini fallback in PredictionService).
        """
        try:
            # Lazy-load the model on first use
            if not self._model_loaded:
                self._ensure_model_loaded()
            
            # If model failed to load, return None to trigger fallback
            if self._model is None:
                logger.warning("Disease model not available; using fallback")
                return None
            
            preprocessed = self._preprocess(image_bytes)
            return await self._run_inference(preprocessed)
        except Exception as exc:
            logger.exception("Disease detection inference failed: %s", exc)
            return None  # Let PredictionService trigger fallback

    def _ensure_model_loaded(self) -> None:
        """Lazy-load the model on first use."""
        if self._model_loaded:
            return
        
        self._model_loaded = True
        try:
            self._model = self._load_model()
            if self._model is None:
                logger.warning("DiseaseModelService: model could not be loaded; will use Gemini fallback")
                self._model_load_error = "Model file not found or TensorFlow not available"
        except Exception as exc:
            logger.error("DiseaseModelService: failed to load model: %s", exc)
            self._model_load_error = str(exc)
            self._model = None

    # ── Private helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _resolve_path(path_value: str) -> Path:
        """Resolve relative config paths from backend root for stable startup CWD."""
        candidate = Path(path_value)
        if candidate.is_absolute():
            return candidate
        return (_BACKEND_ROOT / candidate).resolve()

    def _load_model(self):
        """Load a TensorFlow/Keras model from DISEASE_MODEL_PATH."""
        model_path = self._resolve_path(self._model_path)
        if not model_path.exists():
            logger.warning(
                "DiseaseModelService: model file not found at %s; will use Gemini fallback",
                model_path,
            )
            return None

        try:
            import tensorflow as tf
        except Exception as exc:
            logger.warning(
                "DiseaseModelService: TensorFlow not available (%s); will use Gemini fallback",
                exc,
            )
            return None

        try:
            model = tf.keras.models.load_model(model_path)
        except AttributeError:
            # Some environments expose TensorFlow ops but not tf.keras.
            # Fall back to standalone Keras package installed with TF 2.16+.
            try:
                import keras
                model = keras.models.load_model(model_path)
            except Exception as exc:
                logger.error(
                    "DiseaseModelService: Failed to load model with Keras: %s. "
                    "This may be due to Keras/TensorFlow version mismatch. "
                    "Will use Gemini fallback for predictions.",
                    exc,
                )
                return None
        except TypeError as exc:
            # Handle Keras version compatibility issues (e.g., BatchNormalization params)
            if "BatchNormalization" in str(exc) or "renorm" in str(exc):
                logger.error(
                    "DiseaseModelService: Keras model has incompatible parameters. "
                    "This is likely due to TensorFlow/Keras version mismatch. "
                    "The saved model was created with an older Keras version. "
                    "Will use Gemini fallback for predictions. "
                    "To fix: retrain the model with the current TensorFlow version."
                )
                return None
            raise
        except Exception as exc:
            logger.error(
                "DiseaseModelService: Failed to load model: %s. Will use Gemini fallback.",
                exc,
            )
            return None

        # Align preprocessing size with the model's expected input shape.
        input_shape = getattr(model, "input_shape", None)
        if isinstance(input_shape, tuple) and len(input_shape) >= 3:
            h, w = input_shape[1], input_shape[2]
            if isinstance(h, int) and isinstance(w, int):
                self._INPUT_SIZE = (h, w)
                logger.info(
                    "DiseaseModelService: using model input size %sx%s",
                    h,
                    w,
                )

        logger.info("DiseaseModelService: model loaded from %s", model_path)
        return model

    def _load_label_map(self) -> list[tuple[str, str]]:
        """Load label map from JSON file; fallback to stub labels if missing."""
        label_map_path = self._resolve_path(settings.DISEASE_LABEL_MAP_PATH)
        if not label_map_path.exists():
            logger.warning(
                "DiseaseModelService: label map missing at %s; using stub labels",
                label_map_path,
            )
            return _STUB_LABEL_MAP

        try:
            raw = json.loads(label_map_path.read_text(encoding="utf-8"))
            ordered = sorted(raw, key=lambda x: int(x["index"]))
            parsed = [
                (str(item["plant_name"]), str(item["disease_name"]))
                for item in ordered
            ]
            if not parsed:
                raise ValueError("label map is empty")
            logger.info("DiseaseModelService: loaded %d labels", len(parsed))
            return parsed
        except Exception as exc:
            logger.warning(
                "DiseaseModelService: failed to parse label map (%s); using stub labels",
                exc,
            )
            return _STUB_LABEL_MAP

    def _preprocess(self, image_bytes: bytes):
        """Prepare image tensor in NHWC format using raw pixel range [0, 255]."""
        try:
            import tensorflow as tf
        except Exception as exc:
            raise RuntimeError(
                "tensorflow is required for disease model preprocessing"
            ) from exc

        target_h, target_w = self._INPUT_SIZE
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        # PIL expects size as (width, height).
        img = img.resize((target_w, target_h))

        # Keep 0..255 range; training graph already applies MobileNet preprocessing.
        arr = np.asarray(img, dtype=np.float32)
        tensor = tf.convert_to_tensor(arr, dtype=tf.float32)
        return tf.expand_dims(tensor, axis=0)

    async def _run_inference(self, preprocessed_image) -> DiseaseDetectionResult:
        """Run model inference and map top class to plant + disease labels."""
        if self._model is None:
            logger.info("DiseaseModelService: no model loaded, returning None for fallback")
            return None

        try:
            import tensorflow as tf
        except Exception as exc:
            raise RuntimeError(
                "tensorflow is required for disease model inference"
            ) from exc

        probs = self._model.predict(preprocessed_image, verbose=0)[0]
        probs_tensor = tf.convert_to_tensor(probs, dtype=tf.float32)
        top_idx = int(tf.argmax(probs_tensor).numpy())
        confidence = float(probs_tensor[top_idx].numpy())

        if top_idx >= len(self._label_map):
            logger.warning("DiseaseModelService: class index %d out of label map bounds", top_idx)
            return None

        plant_name, disease_name = self._label_map[top_idx]
        all_classes = {
            f"{p}/{d}": float(probs[i])
            for i, (p, d) in enumerate(self._label_map)
            if i < len(probs)
        }

        return DiseaseDetectionResult(
            plant_name=plant_name,
            disease_name=disease_name,
            confidence_score=confidence,
            all_classes=all_classes,
            model_version=Path(self._model_path).name,
        )
