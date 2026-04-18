"""
Prediction and history Pydantic schemas.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── AI Response schemas ───────────────────────────────────────────────────────


class AIResponseSchema(BaseModel):
    id: UUID
    language: str
    precautions_text: Optional[str]
    audio_url: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Prediction schemas ────────────────────────────────────────────────────────


class PredictionSchema(BaseModel):
    id: UUID
    upload_id: UUID
    plant_name: Optional[str]
    disease_name: Optional[str]
    confidence_score: Optional[float]
    is_plant: bool
    fallback_used: bool
    created_at: datetime
    ai_responses: List[AIResponseSchema] = []

    model_config = {"from_attributes": True}


class UploadSchema(BaseModel):
    id: UUID
    user_id: UUID
    image_url: str
    uploaded_at: datetime
    prediction: Optional[PredictionSchema] = None

    model_config = {"from_attributes": True}


# ── Predict response ──────────────────────────────────────────────────────────


class PlantValidationResult(BaseModel):
    is_plant: bool
    confidence: float
    message: str


class DiseaseDetectionResult(BaseModel):
    plant_name: str
    disease_name: str
    confidence_score: float
    fallback_used: bool = False


class PredictResponse(BaseModel):
    upload_id: UUID
    prediction_id: UUID
    is_plant: bool
    plant_name: Optional[str]
    disease_name: Optional[str]
    confidence_score: Optional[float]
    fallback_used: bool
    precautions: Optional[str]
    audio_url: Optional[str] = None
    language: str = "en"  # ISO 639-1 language code used for precautions


# ── History schemas ───────────────────────────────────────────────────────────


class HistoryItem(BaseModel):
    upload_id: UUID
    prediction_id: Optional[UUID]
    image_url: str
    plant_name: Optional[str]
    disease_name: Optional[str]
    confidence_score: Optional[float]
    is_plant: bool
    fallback_used: bool
    uploaded_at: datetime
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


class HistoryResponse(BaseModel):
    items: List[HistoryItem]
    total: int
    page: int
    page_size: int
    has_next: bool
