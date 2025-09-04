from __future__ import annotations

from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.organization import Organization
from .base import BaseRepository


class OrganizationRepository(BaseRepository[Organization]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Organization)

    async def get_by_salesforce_org(self, salesforce_org_id: str) -> Optional[Organization]:
        result = await self.session.execute(
            select(Organization).where(Organization.salesforce_org_id == salesforce_org_id)
        )
        return result.scalar_one_or_none()

    async def is_feature_enabled(self, org_id, feature: str) -> bool:
        result = await self.session.execute(select(Organization).where(Organization.id == org_id))
        org = result.scalar_one_or_none()
        if not org:
            return False
        features = org.features or []
        return feature in features
