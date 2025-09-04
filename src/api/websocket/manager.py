from __future__ import annotations

from typing import Dict
from fastapi import WebSocket


class WebSocketManager:
    def __init__(self):
        self.active: Dict[str, WebSocket] = {}

    async def connect(self, key: str, ws: WebSocket) -> None:
        await ws.accept()
        self.active[key] = ws

    async def disconnect(self, key: str) -> None:
        ws = self.active.pop(key, None)
        if ws:
            await ws.close()

    async def send_text(self, key: str, message: str) -> None:
        ws = self.active.get(key)
        if ws:
            await ws.send_text(message)
