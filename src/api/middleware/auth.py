from __future__ import annotations

from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import jwt

from src.core.config import get_settings
from src.core.exceptions import AuthenticationError


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.settings = get_settings()

    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:
        path = request.url.path
        # Public endpoints
        if path.startswith("/api/health") or path.startswith("/api/ready") or path.startswith("/api/auth/"):
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.lower().startswith("bearer "):
            raise AuthenticationError("Missing or invalid Authorization header")

        token = auth_header.split(" ", 1)[1].strip()
        try:
            payload = jwt.decode(
                token,
                self.settings.security.secret_key,  # type: ignore[attr-defined]
                algorithms=[self.settings.security.jwt.algorithm],  # type: ignore[attr-defined]
                audience=self.settings.security.jwt.audience,
                issuer=self.settings.security.jwt.issuer,
            )
            # attach identity to scope
            request.state.user = {
                "sub": payload.get("sub"),
                "scopes": payload.get("scopes", []),
            }
        except Exception as e:
            raise AuthenticationError(f"Invalid token: {e}")

        return await call_next(request)
