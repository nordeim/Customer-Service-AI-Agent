from __future__ import annotations

from fastapi import FastAPI, WebSocket

from .manager import WebSocketManager
from .auth import authenticate_websocket


manager = WebSocketManager()


def register_websocket_routes(app: FastAPI) -> None:
    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket):
        identity = await authenticate_websocket(ws)
        key = identity["sub"] or ws.client.host
        await manager.connect(key, ws)
        try:
            while True:
                data = await ws.receive_text()
                await manager.send_text(key, f"echo: {data}")
        except Exception:
            await manager.disconnect(key)
