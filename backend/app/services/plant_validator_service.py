"""
Plant Validator Service (stub).

─────────────────────────────────────────────────────────────────────────────
PRODUCTION NOTE
─────────────────────────────────────────────────────────────────────────────
Replace the `_run_inference` method with your trained CNN model loader.
The public `validate` interface is intentionally stable so every caller
(prediction_service, tests) is unaffected by the swap.

Expected swap surface:
    1. Load your SavedModel / .h5 / ONNX file in __init__
    2. Preprocess the image to match training input shape
    3. Return confidence from the softmax/sigmoid output
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass

from PIL import Image

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Data contract ─────────────────────────────────────────────────────────────


@dataclass
class PlantValidationResult:
    is_plant: bool
    confidence: float        # 0.0 – 1.0
    message: str


# ── Service ───────────────────────────────────────────────────────────────────


class PlantValidatorService:
    """
    Validates whether a raw image contains a plant.

    Instantiate once at application startup (singleton pattern) and inject
    into PredictionService via dependency injection.
    """

    # Target input shape expected by the real model
    _INPUT_SIZE: tuple[int, int] = (224, 224)

    def __init__(self, model_path: str = settings.PLANT_VALIDATOR_MODEL_PATH) -> None:
        self._model_path = model_path
        self._model = self._load_model()

    # ── Public API ─────────────────────────────────────────────────────────────

    async def validate(self, image_bytes: bytes) -> PlantValidationResult:
        """
        Validate *image_bytes* and return a PlantValidationResult.

        This is the only method callers should use.
        """
        try:
            preprocessed = self._preprocess(image_bytes)
            confidence = await self._run_inference(preprocessed)
        except Exception as exc:
            logger.exception("Plant validation inference failed: %s", exc)
            # Fail open — treat as plant so downstream can still attempt
            # disease detection; fallback logic will cover it.
            return PlantValidationResult(
                is_plant=True,
                confidence=0.0,
                message="Validation model unavailable — assuming plant",
            )

        is_plant = confidence >= settings.CONFIDENCE_THRESHOLD
        return PlantValidationResult(
            is_plant=is_plant,
            confidence=round(confidence, 4),
            message=(
                "Image classified as a plant"
                if is_plant
                else "Image does not appear to be a plant"
            ),
        )

    # ── Private helpers ────────────────────────────────────────────────────────

    def _load_model(self):
        """
        [STUB] Load the plant-validation CNN model from *self._model_path*.

        Replace this with:
            import tensorflow as tf
            return tf.keras.models.load_model(self._model_path)
        or equivalent for PyTorch / ONNX Runtime.
        """
        logger.info(
            "PlantValidatorService: model stub loaded (path=%s)",
            self._model_path,
        )
        return None  # Stub: no real model loaded

    def _preprocess(self, image_bytes: bytes):
        """
        Resize and normalise image bytes for model input.

        [STUB] For a real CNN, also convert to a numpy array and scale to [0,1].
        """
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img = img.resize(self._INPUT_SIZE)
        # Real implementation: return np.array(img) / 255.0
        return img

    async def _run_inference(self, preprocessed_image) -> float:
        """
        [STUB] Run the model and return confidence that the image is a plant.

        Real implementation (TensorFlow example):
            import numpy as np
            input_tensor = np.expand_dims(preprocessed_image, axis=0)
            predictions = self._model.predict(input_tensor)
            return float(predictions[0][1])   # index 1 = "plant" class
        """
        # Stub always returns high confidence so the pipeline continues
        logger.debug("PlantValidatorService: returning stub confidence 0.92")
        return 0.92
