from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import CoreSchemaBase, UUIDPkMixin, TimestampMixin


class Conversation(CoreSchemaBase, UUIDPkMixin, TimestampMixin):
    __tablename__ = "conversations"

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("core.users.id"), nullable=False)

    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active")
    priority: Mapped[int] = mapped_column(Integer, default=2)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    message_count: Mapped[int] = mapped_column(Integer, default=0)
    user_message_count: Mapped[int] = mapped_column(Integer, default=0)
    ai_message_count: Mapped[int] = mapped_column(Integer, default=0)

    ai_confidence_avg: Mapped[Optional[float]] = mapped_column()
    sentiment_score_avg: Mapped[Optional[float]] = mapped_column()
    emotion_trajectory: Mapped[list] = mapped_column(JSON, default=list)

    resolution_type: Mapped[Optional[str]] = mapped_column(String(50))
    resolution_time_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    resolution_summary: Mapped[Optional[str]] = mapped_column(String)

    escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    escalation_reason: Mapped[Optional[str]] = mapped_column(String(255))
    escalated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    escalated_to: Mapped[Optional[str]] = mapped_column(String(255))

    satisfaction_score: Mapped[Optional[float]] = mapped_column()
    satisfaction_feedback: Mapped[Optional[str]] = mapped_column(String)
    satisfaction_submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    context: Mapped[dict] = mapped_column(JSON, default=dict)
    context_switches: Mapped[list] = mapped_column(JSON, default=list)
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)
