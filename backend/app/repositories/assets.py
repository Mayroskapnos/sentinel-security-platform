from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.schemas.asset import AssetFilters


class AssetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _filtered_query(filters: AssetFilters) -> Select[tuple[Asset]]:
        query = select(Asset)
        if filters.asset_type:
            query = query.where(Asset.asset_type == filters.asset_type)
        if filters.status:
            query = query.where(Asset.status == filters.status)
        if filters.network_zone:
            query = query.where(Asset.network_zone == filters.network_zone)
        if filters.criticality:
            query = query.where(Asset.criticality == filters.criticality)
        if filters.min_risk_score is not None:
            query = query.where(Asset.risk_score >= filters.min_risk_score)
        if filters.search:
            search = f"%{filters.search.strip()}%"
            query = query.where(
                or_(
                    Asset.hostname.ilike(search),
                    Asset.display_name.ilike(search),
                    Asset.ip_address.ilike(search),
                )
            )
        return query

    async def list(self, filters: AssetFilters) -> tuple[list[Asset], int]:
        base_query = self._filtered_query(filters)
        total = await self.session.scalar(
            select(func.count()).select_from(base_query.order_by(None).subquery())
        )
        result = await self.session.scalars(
            base_query.order_by(Asset.risk_score.desc(), Asset.hostname)
            .offset((filters.page - 1) * filters.page_size)
            .limit(filters.page_size)
        )
        return list(result), int(total or 0)

    async def get(self, asset_id: UUID) -> Asset | None:
        return await self.session.get(Asset, asset_id)

    async def get_by_hostname(self, hostname: str) -> Asset | None:
        return await self.session.scalar(select(Asset).where(Asset.hostname == hostname))

    async def get_by_ip_addresses(self, ip_addresses: Sequence[str]) -> Sequence[Asset]:
        if not ip_addresses:
            return []
        result = await self.session.scalars(
            select(Asset)
            .where(Asset.ip_address.in_(ip_addresses))
            .order_by(Asset.ip_address, Asset.id)
        )
        return list(result)

    async def create(self, asset: Asset) -> Asset:
        self.session.add(asset)
        await self.session.flush()
        await self.session.refresh(asset)
        return asset
