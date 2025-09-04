from __future__ import annotations

import uuid
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db_session
from src.repositories.conversation import ConversationRepository

router = APIRouter(prefix="/conversations", tags=["conversations"]) 


class CreateConversationRequest(BaseModel):
    user_id: uuid.UUID
    channel: str


@router.post("", status_code=201)
async def create_conversation(payload: CreateConversationRequest, db: AsyncSession = Depends(get_db_session)):
    repo = ConversationRepository(db)
    conv = await repo.create(user_id=payload.user_id, channel=payload.channel, organization_id=uuid.uuid4())
    return {"id": str(conv.id), "status": conv.status, "channel": conv.channel}


@router.get("/{conversation_id}")
async def get_conversation(conversation_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    repo = ConversationRepository(db)
    conv = await repo.get(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Not found")
    return {
        "id": str(conv.id),
        "status": conv.status,
        "message_count": conv.message_count,
        "satisfaction_score": conv.satisfaction_score,
    }
