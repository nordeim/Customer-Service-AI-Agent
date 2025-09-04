from __future__ import annotations

import asyncio
import json

import httpx

# from src.api.main import app
from api.main import app


async def main() -> None:
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        r1 = await client.get("/api/health")
        r2 = await client.get("/api/ready")
        print("/api/health:", r1.status_code, r1.json())
        print("/api/ready:", r2.status_code, r2.json())


if __name__ == "__main__":
    asyncio.run(main())
