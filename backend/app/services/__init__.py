"""
Service singletons — loaded once at application startup.

ML models are expensive to initialise. We create one instance per process
here and re-use it across all requests via FastAPI dependency injection.
"""

from app.services.disease_model_service import DiseaseModelService
from app.services.fallback_service import FallbackService
from app.services.llm_service import LLMService
from app.services.plant_validator_service import PlantValidatorService

# Loaded once at import time (on worker startup)
plant_validator_service = PlantValidatorService()
disease_model_service = DiseaseModelService()
fallback_service = FallbackService()
llm_service = LLMService()

__all__ = [
    "plant_validator_service",
    "disease_model_service",
    "fallback_service",
    "llm_service",
]
