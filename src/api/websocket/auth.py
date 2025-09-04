from __future__ import annotations

from typing import Dict
from fastapi import WebSocket, WebSocketException, status
import jwt

from src.core.config import get_settings


async def authenticate_websocket(websocket: WebSocket) -> Dict:
    token = websocket.query_params.get("token")
    if not token:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
    s = get_settings()
    try:
        payload = jwt.decode(
            token,
            s.security.secret_key,  # type: ignore[attr-defined]
            algorithms=[s.security.jwt.algorithm],  # type: ignore[attr-defined]
            audience=s.security.jwt.audience,
            issuer=s.security.jwt.issuer,
        )
        return {"sub": payload.get("sub")}
    except Exception:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
