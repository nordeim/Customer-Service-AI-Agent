from __future__ import annotations

from typing import AsyncIterator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_sessionmaker
from src.core.config import get_settings


async def get_db_session() -> AsyncIterator[AsyncSession]:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        try:
            yield session
        finally:
            await session.close()


def get_app_settings():
    return get_settings()
