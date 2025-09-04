from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.conversation import Conversation
from .base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Conversation)

    async def get_active_by_user(self, user_id, channel: str) -> Optional[Conversation]:
        result = await self.session.execute(
            select(Conversation).where(
                Conversation.user_id == user_id,
                Conversation.channel == channel,
                Conversation.status.in_(["active", "waiting", "processing"])  # type: ignore[arg-type]
            ).order_by(Conversation.last_activity_at.desc())
        )
        return result.scalar_one_or_none()

    async def mark_escalated(self, conversation_id, reason: str) -> None:
        await self.session.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(escalated=True, escalation_reason=reason, escalated_at=datetime.utcnow())
        )
        await self.session.flush()

    async def close_abandoned(self, timeout_hours: int = 24) -> int:
        cutoff = datetime.utcnow() - timedelta(hours=timeout_hours)
        result = await self.session.execute(
            update(Conversation)
            .where(Conversation.status.in_(["active", "waiting"]))  # type: ignore[arg-type]
            .where(Conversation.last_activity_at < cutoff)
            .values(status="abandoned", ended_at=datetime.utcnow(), resolution_type="abandoned")
            .returning(Conversation.id)
        )
        rows = result.fetchall()
        await self.session.flush()
        return len(rows)
