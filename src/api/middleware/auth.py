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

        # Allow CORS preflight requests through
        if request.method == "OPTIONS":
            return await call_next(request)

        auth_header = request.headers.get("Authorization")

        # In development allow requests without Authorization header to ease local work.
        # In production enforce strict bearer token validation.
        if not auth_header or not auth_header.lower().startswith("bearer "):
            if not self.settings.is_production:
                # Attach a lightweight dev identity for convenience
                request.state.user = {"sub": "dev", "scopes": ["*"]}
                return await call_next(request)
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
            # If token invalid and we're in dev, attach dev identity, otherwise fail
            if not self.settings.is_production:
                request.state.user = {"sub": "dev", "scopes": ["*"]}
                return await call_next(request)
            raise AuthenticationError(f"Invalid token: {e}")

        return await call_next(request)
