"""
Import all models here so that Alembic can discover them for migrations.
"""

from app.models.ai_response import AIResponse
from app.models.prediction import Prediction
from app.models.upload import Upload
from app.models.user import User

__all__ = ["User", "Upload", "Prediction", "AIResponse"]
