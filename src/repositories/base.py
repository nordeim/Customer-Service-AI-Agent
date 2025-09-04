from __future__ import annotations

from typing import Generic, List, Optional, Sequence, Type, TypeVar

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeMeta

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    def __init__(self, session: AsyncSession, model: Type[ModelT]):
        self.session = session
        self.model = model

    async def get(self, obj_id) -> Optional[ModelT]:
        result = await self.session.execute(select(self.model).where(self.model.id == obj_id))
        return result.scalar_one_or_none()

    async def list(self, limit: int = 100, offset: int = 0) -> List[ModelT]:
        result = await self.session.execute(select(self.model).limit(limit).offset(offset))
        return list(result.scalars().all())

    async def create(self, **kwargs) -> ModelT:
        obj = self.model(**kwargs)
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def update(self, obj_id, **kwargs) -> Optional[ModelT]:
        await self.session.execute(update(self.model).where(self.model.id == obj_id).values(**kwargs))
        await self.session.flush()
        return await self.get(obj_id)

    async def delete(self, obj_id) -> None:
        obj = await self.get(obj_id)
        if obj is not None:
            await self.session.delete(obj)  # type: ignore[arg-type]
            await self.session.flush()
