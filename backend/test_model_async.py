#!/usr/bin/env python
"""Test disease model loading with async detection call."""
import os
import asyncio
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

print("=" * 70)
print("Testing Disease Model Service with Async Detection")
print("=" * 70)

from pathlib import Path
from app.core.config import settings
from PIL import Image
import io

# Create a test image
img = Image.new("RGB", (224, 224), color=(100, 150, 200))
buf = io.BytesIO()
img.save(buf, format="JPEG")
test_image_bytes = buf.getvalue()

print(f"\n1. Test image created: {len(test_image_bytes)} bytes")

print(f"\n2. Config:")
print(f"   DISEASE_MODEL_PATH: {settings.DISEASE_MODEL_PATH}")

model_path = Path(settings.DISEASE_MODEL_PATH)
print(f"   Resolved: {model_path.resolve()}")
print(f"   Exists: {model_path.exists()}")

print(f"\n3. Initializing DiseaseModelService...")
from app.services.disease_model_service import DiseaseModelService

service = DiseaseModelService()
print(f"   Before any detection:")
print(f"     - _model_loaded: {service._model_loaded}")
print(f"     - _model is None: {service._model is None}")

print(f"\n4. Calling detect() to trigger lazy loading...")
async def test_detect():
    result = await service.detect(test_image_bytes)
    print(f"   After detect() call:")
    print(f"     - _model_loaded: {service._model_loaded}")
    print(f"     - _model is None: {service._model is None}")
    print(f"     - _model_load_error: {service._model_load_error}")
    print(f"     - Result: {result}")
    return result

result = asyncio.run(test_detect())

print("\n" + "=" * 70)
