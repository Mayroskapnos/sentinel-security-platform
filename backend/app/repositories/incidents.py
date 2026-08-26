from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models.alert import Alert, AlertEvent
from app.models.asset import Asset
from app.models.incident import Incident, IncidentAlert, IncidentAsset
from app.models.security_event import SecurityEvent
from app.schemas.incident import IncidentFilters

ACTIVE_INCIDENT_STATUSES = ("open", "investigating")


class IncidentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _filtered_query(filters: IncidentFilters) -> Select[tuple[Incident]]:
        query = select(Incident)
        if filters.severity:
            query = query.where(Incident.severity == filters.severity)
        if filters.status:
            query = query.where(Incident.status == filters.status)
        if filters.asset_id:
            query = query.where(
                exists(
                    select(IncidentAsset.asset_id).where(
                        IncidentAsset.incident_id == Incident.id,
                        IncidentAsset.asset_id == filters.asset_id,
                    )
                )
            )
        if filters.scenario_run_id:
            query = query.where(Incident.scenario_run_id == filters.scenario_run_id)
        if filters.confidence_min is not None:
            query = query.where(Incident.confidence_score >= filters.confidence_min)
        if filters.start_time:
            query = query.where(Incident.last_activity_at >= filters.start_time)
        if filters.end_time:
            query = query.where(Incident.first_activity_at <= filters.end_time)
        if filters.search and filters.search.strip():
            pattern = f"%{filters.search.strip()}%"
            asset_match = exists(
                select(IncidentAsset.asset_id)
                .join(Asset, Asset.id == IncidentAsset.asset_id)
                .where(
                    IncidentAsset.incident_id == Incident.id,
                    Asset.hostname.ilike(pattern),
                )
            )
            query = query.where(
                or_(
                    Incident.incident_number.ilike(pattern),
                    Incident.title.ilike(pattern),
                    asset_match,
                )
            )
        return query

    @staticmethod
    def _detail_options():
        alert_link = selectinload(Incident.alert_links).selectinload(IncidentAlert.alert)
        return (
            selectinload(Incident.asset_links).joinedload(IncidentAsset.asset),
            alert_link.joinedload(Alert.detection_rule),
            alert_link.joinedload(Alert.asset),
            joinedload(Incident.scenario_run),
        )

    async def list(self, filters: IncidentFilters) -> tuple[list[Incident], int]:
        query = self._filtered_query(filters)
        total = int(
            await self.session.scalar(
                select(func.count()).select_from(query.order_by(None).subquery())
            )
            or 0
        )
        incidents = await self.session.scalars(
            query.options(
                selectinload(Incident.asset_links).joinedload(IncidentAsset.asset),
                selectinload(Incident.alert_links),
            )
            .order_by(Incident.last_activity_at.desc(), Incident.id.desc())
            .offset((filters.page - 1) * filters.page_size)
            .limit(filters.page_size)
        )
        return list(incidents.unique()), total

    async def get(self, incident_id: UUID) -> Incident | None:
        return await self.session.scalar(
            select(Incident).where(Incident.id == incident_id).options(*self._detail_options())
        )

    async def for_alert(self, alert_id: UUID) -> Incident | None:
        return await self.session.scalar(
            select(Incident)
            .join(IncidentAlert, IncidentAlert.incident_id == Incident.id)
            .where(IncidentAlert.alert_id == alert_id)
            .options(*self._detail_options())
        )

    async def for_scenario(self, scenario_run_id: UUID) -> Incident | None:
        return await self.session.scalar(
            select(Incident)
            .where(Incident.scenario_run_id == scenario_run_id)
            .order_by(Incident.last_activity_at.desc())
            .options(*self._detail_options())
            .limit(1)
        )

    async def candidates(
        self,
        *,
        window_start: datetime,
        window_end: datetime,
        limit: int,
    ) -> list[Incident]:
        incidents = await self.session.scalars(
            select(Incident)
            .where(
                Incident.status.in_(ACTIVE_INCIDENT_STATUSES),
                Incident.last_activity_at >= window_start,
                Incident.first_activity_at <= window_end,
            )
            .options(*self._detail_options())
            .order_by(Incident.last_activity_at.desc(), Incident.id)
            .limit(limit)
        )
        return list(incidents.unique())

    async def evidence_events(self, incident_id: UUID, limit: int = 2_500) -> list[SecurityEvent]:
        events = await self.session.scalars(
            select(SecurityEvent)
            .join(AlertEvent, AlertEvent.event_id == SecurityEvent.id)
            .join(IncidentAlert, IncidentAlert.alert_id == AlertEvent.alert_id)
            .where(IncidentAlert.incident_id == incident_id)
            .order_by(SecurityEvent.timestamp, SecurityEvent.id)
            .limit(limit)
        )
        return list(events.unique())

    async def event_ids(self, incident_id: UUID, limit: int = 5_000) -> list[UUID]:
        ids = await self.session.scalars(
            select(SecurityEvent.id)
            .join(AlertEvent, AlertEvent.event_id == SecurityEvent.id)
            .join(IncidentAlert, IncidentAlert.alert_id == AlertEvent.alert_id)
            .where(IncidentAlert.incident_id == incident_id)
            .order_by(SecurityEvent.timestamp, SecurityEvent.id)
            .limit(limit)
        )
        return list(dict.fromkeys(ids))
