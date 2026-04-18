"""
AIResponse repository — all DB operations for the ai_responses table.
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_response import AIResponse


class AIResponseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        prediction_id: UUID,
        language: str,
        precautions_text: Optional[str] = None,
        audio_url: Optional[str] = None,
    ) -> AIResponse:
        ai_response = AIResponse(
            prediction_id=prediction_id,
            language=language,
            precautions_text=precautions_text,
            audio_url=audio_url,
        )
        self._session.add(ai_response)
        await self._session.commit()
        await self._session.refresh(ai_response)
        return ai_response

    async def get_by_prediction_id(
        self, prediction_id: UUID
    ) -> List[AIResponse]:
        result = await self._session.execute(
            select(AIResponse).where(
                AIResponse.prediction_id == prediction_id
            )
        )
        return list(result.scalars().all())

    async def get_by_prediction_and_language(
        self, prediction_id: UUID, language: str
    ) -> Optional[AIResponse]:
        """Fetch cached response for a prediction+language combo."""
        result = await self._session.execute(
            select(AIResponse).where(
                AIResponse.prediction_id == prediction_id,
                AIResponse.language == language,
            )
        )
        return result.scalar_one_or_none()
