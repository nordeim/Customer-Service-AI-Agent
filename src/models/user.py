from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import CoreSchemaBase, UUIDPkMixin, TimestampMixin


class User(CoreSchemaBase, UUIDPkMixin, TimestampMixin):
    __tablename__ = "users"

    organization_id: Mapped["uuid.UUID"] = mapped_column(nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)

    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100))
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    language: Mapped[str] = mapped_column(String(10), default="en")

    preferences: Mapped[dict] = mapped_column(JSON, default=dict)

    status: Mapped[str] = mapped_column(String(50), default="active")
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    __table_args__ = ({"schema": "core"},)
