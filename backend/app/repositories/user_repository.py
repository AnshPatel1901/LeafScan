"""
User repository — all DB operations for the users table.
"""

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

logger = logging.getLogger(__name__)


class UserRepository:
    """Encapsulates all database queries related to users."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, username: str, password_hash: str) -> User:
        logger.debug(f"Creating user in database: {username}")
        user = User(username=username, password_hash=password_hash)
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        logger.info(f"User created in database: {username} (id: {user.id})")
        return user

    async def get_by_id(self, user_id: str | UUID) -> Optional[User]:
        logger.debug(f"Querying user by id: {user_id}")
        if isinstance(user_id, str):
            user_id = UUID(user_id)
        result = await self._session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if user:
            logger.debug(f"User found by id: {user.username} (id: {user_id})")
        else:
            logger.debug(f"User not found by id: {user_id}")
        return user

    async def get_by_username(self, username: str) -> Optional[User]:
        logger.debug(f"Querying user by username: {username}")
        result = await self._session.execute(
            select(User).where(User.username == username.lower())
        )
        user = result.scalar_one_or_none()
        if user:
            logger.debug(f"User found by username: {username} (id: {user.id})")
        else:
            logger.debug(f"User not found by username: {username}")
        return user

    async def username_exists(self, username: str) -> bool:
        logger.debug(f"Checking if username exists: {username}")
        result = await self._session.execute(
            select(User.id).where(User.username == username.lower())
        )
        exists = result.scalar_one_or_none() is not None
        logger.debug(f"Username '{username}' exists: {exists}")
        return exists
