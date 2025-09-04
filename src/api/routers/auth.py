from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.core.config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"]) 


class TokenRequest(BaseModel):
    sub: str
    ttl_seconds: Optional[int] = 900


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime


@router.post("/token", response_model=TokenResponse)
async def issue_token(payload: TokenRequest):
    s = get_settings()
    now = datetime.now(timezone.utc)
    exp = now + timedelta(seconds=payload.ttl_seconds or s.security.jwt.access_ttl_seconds)  # type: ignore[attr-defined]
    token = jwt.encode(
        {
            "sub": payload.sub,
            "aud": s.security.jwt.audience,  # type: ignore[attr-defined]
            "iss": s.security.jwt.issuer,  # type: ignore[attr-defined]
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
        },
        s.security.secret_key,  # type: ignore[attr-defined]
        algorithm=s.security.jwt.algorithm,  # type: ignore[attr-defined]
    )
    return TokenResponse(access_token=token, expires_at=exp)
