from __future__ import annotations

import asyncio
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import redis.asyncio as redis

from src.core.config import get_settings
from src.core.exceptions import RateLimitError  # type: ignore


LUA_SCRIPT = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_time = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local requested = tonumber(ARGV[4])

local entry = redis.call('HMGET', key, 'tokens', 'timestamp')
local tokens = tonumber(entry[1])
local timestamp = tonumber(entry[2])

if tokens == nil then
  tokens = capacity
  timestamp = now
end

local delta = math.max(0, now - timestamp)
local refill = (delta / refill_time) * capacity
local new_tokens = math.min(capacity, tokens + refill)

local allowed = 0
if new_tokens >= requested then
  allowed = 1
  new_tokens = new_tokens - requested
end

redis.call('HMSET', key, 'tokens', new_tokens, 'timestamp', now)
redis.call('EXPIRE', key, math.ceil(refill_time))
return allowed
"""


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        s = get_settings()
        self.capacity = 100  # req per minute default
        self.refill_time = 60.0
        self.redis = redis.from_url(s.datastore.redis_url if hasattr(s, "datastore") else "redis://localhost:6379/0")  # type: ignore
        self.script = self.redis.register_script(LUA_SCRIPT)

    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:
        path = request.url.path
        if path.startswith("/api/health") or path.startswith("/api/ready"):
            return await call_next(request)

        client_id = request.headers.get("X-API-Key") or request.client.host
        key = f"rl:{client_id}"
        now = time.time()
        allowed = await self.script(keys=[key], args=[self.capacity, self.refill_time, now, 1])
        if int(allowed) != 1:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=429, content={"error": "RateLimited", "message": "Too many requests"})

        return await call_next(request)
