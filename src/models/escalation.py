from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import CoreSchemaBase, UUIDPkMixin, TimestampMixin


class Escalation(CoreSchemaBase, UUIDPkMixin, TimestampMixin):
    __tablename__ = "escalations"

    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("core.conversations.id"), nullable=False)

    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(100))
    priority: Mapped[str] = mapped_column(String(20), default="medium")
    severity: Mapped[str] = mapped_column(String(20), default="normal")

    queue_name: Mapped[Optional[str]] = mapped_column(String(100))
    assigned_to: Mapped[Optional[str]] = mapped_column(String(255))
    assigned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    assignment_method: Mapped[Optional[str]] = mapped_column(String(50))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    first_response_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    sla_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    sla_breached: Mapped[bool] = mapped_column(Boolean, default=False)
    sla_breach_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    resolution_notes: Mapped[Optional[str]] = mapped_column(String)
    resolution_category: Mapped[Optional[str]] = mapped_column(String(100))
    resolved_by: Mapped[Optional[str]] = mapped_column(String(255))

    context: Mapped[dict] = mapped_column(JSON, default=dict)
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)
