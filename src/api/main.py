from __future__ import annotations

import uvloop
import asyncio
from datetime import datetime
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.database.connection import init_engine, dispose_engine, health_check
from src.core.config import get_settings
from src.core.logging import get_logger

# Middleware
from src.api.middleware.auth import AuthMiddleware
from src.api.middleware.rate_limit import RateLimitMiddleware
from src.api.middleware.logging import RequestLoggingMiddleware
from src.api.middleware.security import SecurityHeadersMiddleware
from src.api.middleware.cors import get_cors_config

# Routers
from src.api.routers.health import router as health_router
from src.api.routers.auth import router as auth_router
from src.api.routers.conversations import router as conversations_router
from src.api.routers.messages import router as messages_router
from src.api.routers.users import router as users_router

# Websocket
from src.api.websocket.handlers import register_websocket_routes


asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="AI Customer Service Agent API",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # Configure logging
    try:
        get_logger("app")  # This will initialize and configure the logger
    except Exception:
        pass

    # Core lifecycle
    @app.on_event("startup")
    async def _startup() -> None:  # noqa: D401
        init_engine(echo=False)

    @app.on_event("shutdown")
    async def _shutdown() -> None:  # noqa: D401
        await dispose_engine()

    # Middleware: order matters
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(AuthMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    cors = get_cors_config(settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors["allow_origins"],
        allow_credentials=True,
        allow_methods=cors["allow_methods"],
        allow_headers=cors["allow_headers"],
        expose_headers=cors["expose_headers"],
        max_age=cors["max_age"],
    )

    # Routers
    app.include_router(health_router, prefix="/api")
    app.include_router(auth_router, prefix="/api")
    app.include_router(conversations_router, prefix="/api/v1")
    app.include_router(messages_router, prefix="/api/v1")
    app.include_router(users_router, prefix="/api/v1")

    # Websocket routes
    register_websocket_routes(app)

    return app


app = create_app()
