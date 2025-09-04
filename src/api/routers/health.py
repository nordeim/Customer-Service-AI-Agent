# File: src/api/routers/health.py

from __future__ import annotations

from fastapi import APIRouter
from src.database.connection import health_check

router = APIRouter(tags=["health"]) 


@router.get("/health")
async def get_health():
    return {"status": "ok"}


@router.get("/ready")
async def get_ready():
    db_ok = await health_check()
    return {"ready": db_ok, "checks": {"database": db_ok}}
