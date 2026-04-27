"""
Import all models here so that Alembic can discover them for migrations.
"""

from app.models.ai_response import AIResponse
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.models.prediction import Prediction
from app.models.upload import Upload
from app.models.user import User

__all__ = ["User", "Upload", "Prediction", "AIResponse", "ChatSession", "ChatMessage"]
