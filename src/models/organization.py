from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, String, Integer, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import CoreSchemaBase, UUIDPkMixin, TimestampMixin


class Organization(CoreSchemaBase, UUIDPkMixin, TimestampMixin):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    salesforce_org_id: Mapped[Optional[str]] = mapped_column(String(18), unique=True)
    subscription_tier: Mapped[str] = mapped_column(String(50), default="standard")

    max_conversations_per_month: Mapped[int] = mapped_column(Integer, default=10000)
    max_users: Mapped[int] = mapped_column(Integer, default=100)
    max_knowledge_entries: Mapped[int] = mapped_column(Integer, default=1000)

    settings: Mapped[dict] = mapped_column(JSON, default=dict)
    features: Mapped[list] = mapped_column(JSON, default=list)

    activated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    suspended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
