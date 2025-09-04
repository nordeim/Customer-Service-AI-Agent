from __future__ import annotations

from typing import List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.message import Message
from .base import BaseRepository


class MessageRepository(BaseRepository[Message]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Message)

    async def list_by_conversation(self, conversation_id, limit: int = 50) -> List[Message]:
        result = await self.session.execute(
            select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def aggregate_ai_metrics(self, conversation_id) -> dict:
        result = await self.session.execute(
            select(
                func.avg(Message.ai_confidence),
                func.avg(Message.sentiment),
                func.avg(Message.processing_time_ms),
                func.sum(Message.tokens_used),
            ).where(Message.conversation_id == conversation_id, Message.sender_type == "ai_agent")
        )
        avg_conf, avg_sent, avg_latency, total_tokens = result.first()
        return {
            "ai_confidence_avg": float(avg_conf) if avg_conf is not None else None,
            "sentiment_score_avg": float(avg_sent) if avg_sent is not None else None,
            "avg_processing_time_ms": float(avg_latency) if avg_latency is not None else None,
            "total_tokens": int(total_tokens) if total_tokens is not None else 0,
        }
