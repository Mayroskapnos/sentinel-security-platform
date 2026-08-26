from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models.alert import Alert
from app.models.detection_rule import DetectionRule
from app.models.enums import AlertStatus
from app.models.incident import IncidentAlert
from app.schemas.alert import AlertFilters


class AlertRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _filtered_query(filters: AlertFilters) -> Select[tuple[Alert]]:
        query = select(Alert)
        if filters.severity:
            query = query.where(Alert.severity == filters.severity)
        if filters.status:
            query = query.where(Alert.status == filters.status)
        if filters.active_only:
            query = query.where(Alert.status.in_([AlertStatus.NEW, AlertStatus.INVESTIGATING]))
        if filters.rule_id:
            query = query.join(Alert.detection_rule).where(DetectionRule.rule_id == filters.rule_id)
        if filters.asset_id:
            query = query.where(Alert.asset_id == filters.asset_id)
        if filters.source_ip:
            query = query.where(Alert.source_ip == filters.source_ip)
        if filters.destination_ip:
            query = query.where(Alert.destination_ip == filters.destination_ip)
        if filters.username:
            query = query.where(Alert.username.ilike(f"%{filters.username.strip()}%"))
        if filters.start_time:
            query = query.where(Alert.timestamp >= filters.start_time)
        if filters.end_time:
            query = query.where(Alert.timestamp <= filters.end_time)
        return query

    async def list(self, filters: AlertFilters) -> tuple[list[Alert], int]:
        query = self._filtered_query(filters)
        total = await self.session.scalar(
            select(func.count()).select_from(query.order_by(None).subquery())
        )
        alerts = await self.session.scalars(
            query.options(
                joinedload(Alert.detection_rule),
                joinedload(Alert.asset),
                selectinload(Alert.incident_link).joinedload(IncidentAlert.incident),
            )
            .order_by(Alert.timestamp.desc(), Alert.id.desc())
            .offset((filters.page - 1) * filters.page_size)
            .limit(filters.page_size)
        )
        return list(alerts.unique()), int(total or 0)

    async def get(self, alert_id: UUID, *, include_events: bool = False) -> Alert | None:
        options = [
            joinedload(Alert.detection_rule),
            joinedload(Alert.asset),
            selectinload(Alert.incident_link).joinedload(IncidentAlert.incident),
        ]
        if include_events:
            options.append(selectinload(Alert.evidence_events))
        return await self.session.scalar(
            select(Alert).where(Alert.id == alert_id).options(*options)
        )
