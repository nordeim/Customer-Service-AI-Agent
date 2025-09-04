# File: src/api/routers/health.py

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db_session
from src.database.connection import health_check

router = APIRouter()


@router.get("/health", tags=["health"])
async def get_health():
    """Basic liveness probe to confirm the service is running."""
    return {"status": "ok"}


@router.get("/ready", tags=["health"])
async def get_ready(db: AsyncSession = Depends(get_db_session)):
    """
    Readiness probe to confirm the service can connect to its dependencies.
    This will raise an exception if the database connection fails.
    """
    await health_check(db)
    return {"status": "ready"}
