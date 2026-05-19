#!/usr/bin/env python
"""Quick test to check disease model loading."""
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

print("=" * 70)
print("Testing Disease Model Service Initialization")
print("=" * 70)

from pathlib import Path
from app.core.config import settings

print(f"\n1. Config Settings:")
print(f"   DISEASE_MODEL_PATH: {settings.DISEASE_MODEL_PATH}")
print(f"   DISEASE_LABEL_MAP_PATH: {settings.DISEASE_LABEL_MAP_PATH}")

model_path = Path(settings.DISEASE_MODEL_PATH).resolve()
label_path = Path(settings.DISEASE_LABEL_MAP_PATH).resolve()
print(f"\n2. Resolved Paths:")
print(f"   Model: {model_path}")
print(f"   Model exists: {model_path.exists()}")
print(f"   Label map: {label_path}")
print(f"   Label map exists: {label_path.exists()}")

print(f"\n3. Initializing DiseaseModelService...")
from app.services.disease_model_service import DiseaseModelService

service = DiseaseModelService()
print(f"   Service initialized")

print(f"\n4. Checking model status:")
print(f"   Model loaded: {service._model is not None}")
print(f"   Model load error: {service._model_load_error}")

if service._model is not None:
    print(f"   ✅ Model is available!")
    print(f"   Input shape: {service._model.input_shape}")
else:
    print(f"   ❌ Model is NOT available (will use Gemini fallback)")

print(f"\n5. Label map loaded: {len(service._label_map)} classes")
for i, (plant, disease) in enumerate(service._label_map[:5]):
    print(f"   {i}: {plant} / {disease}")

print("\n" + "=" * 70)
