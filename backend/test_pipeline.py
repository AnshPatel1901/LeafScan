#!/usr/bin/env python
"""Comprehensive test of the prediction pipeline."""
import asyncio
import io
import os
import time
from pathlib import Path
from PIL import Image

# Verify environment setup
print("=" * 70)
print("STEP 1: Environment Variables")
print("=" * 70)
print(f"CUDA_VISIBLE_DEVICES: {os.environ.get('CUDA_VISIBLE_DEVICES', 'NOT SET')}")
print(f"TF_ENABLE_ONEDNN_OPTS: {os.environ.get('TF_ENABLE_ONEDNN_OPTS', 'NOT SET')}")

# Test TensorFlow import
print("\n" + "=" * 70)
print("STEP 2: TensorFlow Import")
print("=" * 70)
start = time.time()
print("Importing TensorFlow...")
import tensorflow as tf
elapsed = time.time() - start
print(f"✓ TensorFlow {tf.__version__} imported in {elapsed:.1f} seconds")

# Test model file exists
print("\n" + "=" * 70)
print("STEP 3: Model File Check")
print("=" * 70)
model_path = Path("models/disease_model.keras")
print(f"Model path: {model_path.resolve()}")
print(f"Exists: {model_path.exists()}")
if model_path.exists():
    size_mb = model_path.stat().st_size / (1024 * 1024)
    print(f"Size: {size_mb:.1f} MB")

# Test disease model service initialization
print("\n" + "=" * 70)
print("STEP 4: DiseaseModelService Initialization")
print("=" * 70)
print("Creating service...")
from app.services.disease_model_service import DiseaseModelService
service = DiseaseModelService()
print(f"✓ Service created")
print(f"  _model is None (lazy loading): {service._model is None}")
print(f"  _model_load_error: {service._model_load_error}")
print(f"  _label_map entries: {len(service._label_map)}")

# Create test image
print("\n" + "=" * 70)
print("STEP 5: Create Test Image")
print("=" * 70)
img = Image.new("RGB", (224, 224), color=(100, 150, 200))
buf = io.BytesIO()
img.save(buf, format="JPEG")
test_image_bytes = buf.getvalue()
print(f"✓ Test image created: {len(test_image_bytes)} bytes")

# Test detection (triggers lazy loading)
print("\n" + "=" * 70)
print("STEP 6: Detection Call (Triggers Lazy Loading)")
print("=" * 70)
print("Calling detect()...")

async def test_predict():
    start = time.time()
    print(f"  Before detect(): _model_loaded={service._model_loaded}, _model={service._model is None}")
    
    result = await service.detect(test_image_bytes)
    
    elapsed = time.time() - start
    print(f"  After detect(): {elapsed:.1f} seconds")
    print(f"  _model_loaded: {service._model_loaded}")
    print(f"  _model is None: {service._model is None}")
    print(f"  _model_load_error: {service._model_load_error}")
    print(f"  Result: {result}")
    
    if result:
        print(f"\n✓ PREDICTION SUCCESSFUL:")
        print(f"  Plant: {result.plant_name}")
        print(f"  Disease: {result.disease_name}")
        print(f"  Confidence: {result.confidence_score:.2%}")
    else:
        print(f"\n❌ PREDICTION FAILED (returned None)")

asyncio.run(test_predict())

print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)
