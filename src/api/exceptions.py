from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.core.exceptions import (
    AppError,
    AuthenticationError,
    AuthorizationError,
    ValidationError,
    NotFoundError,
    RepositoryError,
)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        status = 400
        if isinstance(exc, AuthenticationError):
            status = 401
        elif isinstance(exc, AuthorizationError):
            status = 403
        elif isinstance(exc, NotFoundError):
            status = 404
        return JSONResponse(
            status_code=status,
            content={
                "error": exc.code or exc.__class__.__name__,
                "message": str(exc),
                "path": str(request.url.path),
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={
                "error": "InternalServerError",
                "message": "An unexpected error occurred.",
                "path": str(request.url.path),
            },
        )
