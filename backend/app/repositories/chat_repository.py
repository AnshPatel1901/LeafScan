"""
Repository for chat sessions and messages.
All methods are scoped to a user_id to ensure strict data isolation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession


class ChatRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── Sessions ──────────────────────────────────────────────────────────────

    async def create_session(
        self,
        user_id: uuid.UUID,
        title: str = "New Chat",
    ) -> ChatSession:
        session = ChatSession(user_id=user_id, title=title)
        self._db.add(session)
        await self._db.commit()
        await self._db.refresh(session)
        return session

    async def get_sessions_by_user(self, user_id: uuid.UUID) -> List[ChatSession]:
        """Return all sessions for a user ordered by most recently updated."""
        result = await self._db.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get_session(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[ChatSession]:
        """Get a single session, enforcing user ownership."""
        result = await self._db.execute(
            select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def update_session_title(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        title: str,
    ) -> bool:
        result = await self._db.execute(
            update(ChatSession)
            .where(ChatSession.id == session_id, ChatSession.user_id == user_id)
            .values(title=title, updated_at=datetime.now(timezone.utc))
        )
        await self._db.commit()
        return result.rowcount > 0

    async def touch_session(self, session_id: uuid.UUID) -> None:
        """Bump updated_at so the session appears first in the list."""
        await self._db.execute(
            update(ChatSession)
            .where(ChatSession.id == session_id)
            .values(updated_at=datetime.now(timezone.utc))
        )
        await self._db.commit()

    async def delete_session(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        result = await self._db.execute(
            delete(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id,
            )
        )
        await self._db.commit()
        return result.rowcount > 0

    async def get_session_count(self, user_id: uuid.UUID) -> int:
        from sqlalchemy import func
        result = await self._db.execute(
            select(func.count()).select_from(ChatSession).where(
                ChatSession.user_id == user_id
            )
        )
        return result.scalar_one()

    # ── Messages ──────────────────────────────────────────────────────────────

    async def add_message(
        self,
        session_id: uuid.UUID,
        role: str,
        content: str,
        sources: Optional[list] = None,
    ) -> ChatMessage:
        msg = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            sources=sources,
        )
        self._db.add(msg)
        await self._db.commit()
        await self._db.refresh(msg)
        return msg

    async def get_messages(self, session_id: uuid.UUID) -> List[ChatMessage]:
        """Return all messages in a session ordered oldest-first."""
        result = await self._db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_recent_messages(
        self,
        session_id: uuid.UUID,
        limit: int = 20,
    ) -> List[ChatMessage]:
        """Return the most recent N messages for context building."""
        result = await self._db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        rows = list(result.scalars().all())
        rows.reverse()  # Return oldest-first
        return rows
