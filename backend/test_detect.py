import asyncio
import io
from PIL import Image

print("1. Importing service...")
from app.services.disease_model_service import DiseaseModelService

print("2. Creating service...")
service = DiseaseModelService()
print(f"   Model loaded: {service._model is not None}")
print(f"   Error: {service._model_load_error}")

print("3. Creating test image...")
img = Image.new("RGB", (224, 224), color=(100, 150, 200))
buf = io.BytesIO()
img.save(buf, format="JPEG")
test_image = buf.getvalue()

print("4. Calling detect()...")
async def test():
    result = await service.detect(test_image)
    return result

result = asyncio.run(test())
print(f"   Result type: {type(result)}")
print(f"   Result: {result}")

if result:
    print(f"\n✓ SUCCESS!")
    print(f"  Plant: {result.plant_name}")
    print(f"  Disease: {result.disease_name}")
    print(f"  Confidence: {result.confidence_score:.2%}")
else:
    print(f"\n❌ FAILED - model returned None")

print("\nDone!")
