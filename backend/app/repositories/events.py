from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.security_event import SecurityEvent
from app.schemas.security_event import SecurityEventFilters


class SecurityEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _filtered_query(filters: SecurityEventFilters) -> Select[tuple[SecurityEvent]]:
        query = select(SecurityEvent)
        if filters.hostname:
            query = query.where(SecurityEvent.hostname.ilike(f"%{filters.hostname.strip()}%"))
        if filters.asset_id:
            query = query.where(SecurityEvent.asset_id == filters.asset_id)
        if filters.scenario_run_id:
            query = query.where(SecurityEvent.scenario_run_id == filters.scenario_run_id)
        if filters.event_type:
            query = query.where(SecurityEvent.event_type == filters.event_type)
        if filters.source:
            query = query.where(SecurityEvent.source == filters.source)
        if filters.severity:
            query = query.where(SecurityEvent.severity == filters.severity)
        if filters.source_ip:
            query = query.where(SecurityEvent.source_ip == filters.source_ip)
        if filters.destination_ip:
            query = query.where(SecurityEvent.destination_ip == filters.destination_ip)
        if filters.username:
            query = query.where(SecurityEvent.username.ilike(f"%{filters.username.strip()}%"))
        if filters.status:
            query = query.where(SecurityEvent.status == filters.status)
        if filters.start_time:
            query = query.where(SecurityEvent.timestamp >= filters.start_time)
        if filters.end_time:
            query = query.where(SecurityEvent.timestamp <= filters.end_time)
        return query

    async def list(self, filters: SecurityEventFilters) -> tuple[list[SecurityEvent], int]:
        base_query = self._filtered_query(filters)
        total = await self.session.scalar(
            select(func.count()).select_from(base_query.order_by(None).subquery())
        )
        result = await self.session.scalars(
            base_query.options(selectinload(SecurityEvent.asset))
            .order_by(SecurityEvent.timestamp.desc(), SecurityEvent.id.desc())
            .offset((filters.page - 1) * filters.page_size)
            .limit(filters.page_size)
        )
        return list(result), int(total or 0)

    async def get(self, event_id: UUID) -> SecurityEvent | None:
        return await self.session.scalar(
            select(SecurityEvent)
            .where(SecurityEvent.id == event_id)
            .options(selectinload(SecurityEvent.asset))
        )

    async def create(self, event: SecurityEvent) -> SecurityEvent:
        self.session.add(event)
        await self.session.flush()
        await self.session.refresh(event, attribute_names=["asset"])
        return event
