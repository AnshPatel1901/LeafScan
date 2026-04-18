"""
Prediction repository — all DB operations for the predictions table.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.prediction import Prediction


class PredictionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        upload_id: UUID,
        is_plant: bool,
        plant_name: Optional[str] = None,
        disease_name: Optional[str] = None,
        confidence_score: Optional[float] = None,
        fallback_used: bool = False,
    ) -> Prediction:
        prediction = Prediction(
            upload_id=upload_id,
            is_plant=is_plant,
            plant_name=plant_name,
            disease_name=disease_name,
            confidence_score=confidence_score,
            fallback_used=fallback_used,
        )
        self._session.add(prediction)
        await self._session.commit()
        await self._session.refresh(prediction)
        return prediction

    async def get_by_id(self, prediction_id: UUID) -> Optional[Prediction]:
        result = await self._session.execute(
            select(Prediction)
            .where(Prediction.id == prediction_id)
            .options(selectinload(Prediction.ai_responses))
        )
        return result.scalar_one_or_none()

    async def get_by_upload_id(self, upload_id: UUID) -> Optional[Prediction]:
        result = await self._session.execute(
            select(Prediction)
            .where(Prediction.upload_id == upload_id)
            .options(selectinload(Prediction.ai_responses))
        )
        return result.scalar_one_or_none()
