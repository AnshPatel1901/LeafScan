"""
Upload repository — all DB operations for the uploads table.
"""

from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.upload import Upload


class UploadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user_id: UUID, image_url: str) -> Upload:
        upload = Upload(user_id=user_id, image_url=image_url)
        self._session.add(upload)
        await self._session.commit()
        await self._session.refresh(upload)
        return upload

    async def get_by_id(self, upload_id: UUID) -> Optional[Upload]:
        result = await self._session.execute(
            select(Upload)
            .where(Upload.id == upload_id)
            .options(selectinload(Upload.prediction))
        )
        return result.scalar_one_or_none()

    async def get_user_uploads(
        self,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Upload], int]:
        """Return paginated uploads for a user and total count."""
        offset = (page - 1) * page_size

        # Total count
        count_result = await self._session.execute(
            select(func.count(Upload.id)).where(Upload.user_id == user_id)
        )
        total = count_result.scalar_one()

        # Paginated rows
        rows_result = await self._session.execute(
            select(Upload)
            .where(Upload.user_id == user_id)
            .options(selectinload(Upload.prediction))
            .order_by(Upload.uploaded_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        uploads = list(rows_result.scalars().all())

        return uploads, total
