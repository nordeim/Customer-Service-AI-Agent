from __future__ import annotations

from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from .base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def get_by_email(self, organization_id, email: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.organization_id == organization_id, User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_external_id(self, organization_id, external_id: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.organization_id == organization_id, User.external_id == external_id)
        )
        return result.scalar_one_or_none()
