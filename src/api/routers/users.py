from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db_session
from src.repositories.user import UserRepository

router = APIRouter(prefix="/users", tags=["users"]) 


@router.get("")
async def get_user(email: str = Query(...), db: AsyncSession = Depends(get_db_session)):
    repo = UserRepository(db)
    # org id is unknown at this layer; example purpose only
    user = await repo.get_by_email(None, email)  # type: ignore[arg-type]
    if not user:
        raise HTTPException(status_code=404, detail="Not found")
    return {"id": str(user.id), "email": user.email}
