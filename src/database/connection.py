from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import text

try:
    # Prefer application settings when available
    from src.core.config import get_settings  # type: ignore
except Exception:  # pragma: no cover
    get_settings = None  # fallback to env


_engine: Optional[AsyncEngine] = None
_SessionLocal: Optional[async_sessionmaker[AsyncSession]] = None


def _get_database_url() -> str:
    # Try settings first with flexible attribute names to avoid tight coupling
    if get_settings is not None:
        settings = get_settings()
        for attr in (
            "database_url",
            "DATABASE_URL",
            "db_url",
        ):
            if hasattr(settings, attr):
                value = getattr(settings, attr)
                if isinstance(value, str) and value:
                    return value
            if hasattr(settings, "datastore") and hasattr(settings.datastore, attr):
                value = getattr(settings.datastore, attr)
                if isinstance(value, str) and value:
                    return value
    # Fallback to env
    env_val = os.getenv("DATABASE_URL")
    if not env_val:
        raise RuntimeError("DATABASE_URL is not configured")
    return env_val


def init_engine(echo: bool = False, pool_size: int = 10, max_overflow: int = 20) -> AsyncEngine:
    global _engine, _SessionLocal

    if _engine is not None:
        return _engine

    url = _get_database_url()
    _engine = create_async_engine(
        url,
        echo=echo,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_pre_ping=True,
        future=True,
    )
    _SessionLocal = async_sessionmaker(bind=_engine, expire_on_commit=False, autoflush=False, autocommit=False)
    return _engine


def get_engine() -> AsyncEngine:
    if _engine is None:
        return init_engine()
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _SessionLocal
    if _SessionLocal is None:
        init_engine()
    assert _SessionLocal is not None
    return _SessionLocal


@asynccontextmanager
async def transaction_context() -> AsyncIterator[AsyncSession]:
    """Async transactional context: begin → commit/rollback automatically."""
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        try:
            async with session.begin():
                yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def health_check() -> bool:
    """Run a lightweight DB health check."""
    engine = get_engine()
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            _ = result.scalar_one()
        return True
    except Exception:
        return False


async def dispose_engine() -> None:
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
