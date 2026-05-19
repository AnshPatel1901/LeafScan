#!/usr/bin/env python
"""Directly test model loading with verbose output."""
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

print("Step 1: Importing TensorFlow...")
import tensorflow as tf
print(f"✓ TensorFlow version: {tf.__version__}")

from pathlib import Path
model_path = Path("models/disease_model.keras")

print(f"\nStep 2: Checking model file...")
print(f"Model path: {model_path.resolve()}")
print(f"Exists: {model_path.exists()}")

if not model_path.exists():
    print("❌ Model file doesn't exist!")
    exit(1)

file_size = model_path.stat().st_size
print(f"File size: {file_size / (1024*1024):.1f} MB")

print(f"\nStep 3: Loading model with TensorFlow...")
print("(This may take 1-2 minutes on first load...)")

try:
    model = tf.keras.models.load_model(model_path)
    print(f"✅ Model loaded successfully!")
    print(f"Input shape: {model.input_shape}")
    print(f"Output shape: {model.output_shape}")
except Exception as e:
    print(f"❌ Error loading model:")
    print(f"{type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
