import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

print("Importing TensorFlow...")
import tensorflow as tf
print(f"TensorFlow version: {tf.__version__}")

print("\nLoading model...")
try:
    model = tf.keras.models.load_model('models/disease_model.keras')
    print(f"✓ Model loaded!")
    print(f"  Input shape: {model.input_shape}")
    print(f"  Output shape: {model.output_shape}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
