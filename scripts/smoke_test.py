from __future__ import annotations

import asyncio
import json

from httpx import AsyncClient, ASGITransport

from src.api.main import app

async def main() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.get("/api/health")
        r2 = await client.get("/api/ready")
        print("/api/health:", r1.status_code, r1.json())
        print("/api/ready:", r2.status_code, r2.json())


if __name__ == "__main__":
    asyncio.run(main())
