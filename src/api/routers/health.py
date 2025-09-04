from __future__ import annotations

from fastapi import APIRouter
from src.database.connection import health_check

router = APIRouter(prefix="/health", tags=["health"]) 


@router.get("")
async def health():
    return {"status": "ok"}


@router.get("/ready")
async def ready():
    db_ok = await health_check()
    return {"ready": db_ok, "checks": {"database": db_ok}}
