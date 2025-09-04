from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, String, Integer, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import CoreSchemaBase, UUIDPkMixin, TimestampMixin


class Message(CoreSchemaBase, UUIDPkMixin, TimestampMixin):
    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("core.conversations.id", ondelete="CASCADE"), nullable=False)

    sender_type: Mapped[str] = mapped_column(String(20), nullable=False)
    sender_id: Mapped[Optional[str]] = mapped_column(String(255))
    sender_name: Mapped[Optional[str]] = mapped_column(String(255))

    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(50), default="text")
    content_encrypted: Mapped[bool] = mapped_column(Boolean, default=False)

    intent: Mapped[Optional[str]] = mapped_column(String(100))
    intent_confidence: Mapped[Optional[float]] = mapped_column()
    secondary_intents: Mapped[list] = mapped_column(JSON, default=list)
    entities: Mapped[list] = mapped_column(JSON, default=list)
    sentiment: Mapped[Optional[float]] = mapped_column()
    emotion: Mapped[Optional[str]] = mapped_column(String(50))
    emotion_intensity: Mapped[Optional[float]] = mapped_column()

    ai_model_used: Mapped[Optional[str]] = mapped_column(String(100))
    ai_confidence: Mapped[Optional[float]] = mapped_column()
    processing_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    edited_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    attachments: Mapped[list] = mapped_column(JSON, default=list)
    message_data: Mapped[dict] = mapped_column(JSON, default=dict)
