from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db_session
from src.repositories.message import MessageRepository

router = APIRouter(prefix="/messages", tags=["messages"]) 


class PostMessageRequest(BaseModel):
    conversation_id: uuid.UUID
    content: str
    content_type: Optional[str] = "text"


@router.post("", status_code=200)
async def post_message(payload: PostMessageRequest, db: AsyncSession = Depends(get_db_session)):
    repo = MessageRepository(db)
    msg = await repo.create(
        conversation_id=payload.conversation_id,
        sender_type="user",
        content=payload.content,
        content_type=payload.content_type,
    )
    return {"id": str(msg.id), "status": "accepted"}
