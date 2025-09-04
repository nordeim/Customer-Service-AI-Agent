from __future__ import annotations

import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.core.logging import get_logger, request_id_ctx  # type: ignore


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.logger = get_logger("api")

    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request_id_ctx.set(req_id)
        start = time.time()
        response = await call_next(request)
        duration_ms = int((time.time() - start) * 1000)
        self.logger.info(
            "request handled",  # This is the main log message
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        response.headers["X-Request-ID"] = req_id
        return response
