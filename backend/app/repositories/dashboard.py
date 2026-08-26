from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.asset import Asset
from app.models.enums import AlertStatus, AssetStatus, IncidentStatus
from app.models.incident import Incident
from app.models.security_event import SecurityEvent


class DashboardRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def summary(self, now: datetime) -> dict[str, int]:
        start_of_day = now.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        one_hour_ago = now - timedelta(hours=1)
        row = (
            await self.session.execute(
                select(
                    func.count(Asset.id).label("total_assets"),
                    func.count(Asset.id)
                    .filter(Asset.status == AssetStatus.ONLINE)
                    .label("online_assets"),
                    func.count(Asset.id).filter(Asset.risk_score >= 61).label("high_risk_assets"),
                )
            )
        ).one()
        event_row = (
            await self.session.execute(
                select(
                    func.count(SecurityEvent.id)
                    .filter(SecurityEvent.timestamp >= start_of_day)
                    .label("events_today"),
                    func.count(SecurityEvent.id)
                    .filter(SecurityEvent.timestamp >= one_hour_ago)
                    .label("events_last_hour"),
                )
            )
        ).one()
        alert_row = (
            await self.session.execute(
                select(
                    func.count(Alert.id)
                    .filter(Alert.status.in_([AlertStatus.NEW, AlertStatus.INVESTIGATING]))
                    .label("open_alerts"),
                    func.count(Alert.id)
                    .filter(
                        Alert.status.in_([AlertStatus.NEW, AlertStatus.INVESTIGATING]),
                        Alert.severity == "critical",
                    )
                    .label("critical_alerts"),
                    func.count(Alert.id)
                    .filter(
                        Alert.status.in_([AlertStatus.NEW, AlertStatus.INVESTIGATING]),
                        Alert.severity == "high",
                    )
                    .label("high_alerts"),
                )
            )
        ).one()
        incident_row = (
            await self.session.execute(
                select(
                    func.count(Incident.id)
                    .filter(
                        Incident.status.in_([IncidentStatus.OPEN, IncidentStatus.INVESTIGATING])
                    )
                    .label("open_incidents"),
                    func.count(Incident.id)
                    .filter(
                        Incident.status.in_([IncidentStatus.OPEN, IncidentStatus.INVESTIGATING]),
                        Incident.severity == "critical",
                    )
                    .label("critical_incidents"),
                )
            )
        ).one()
        return {
            "total_assets": int(row.total_assets),
            "online_assets": int(row.online_assets),
            "high_risk_assets": int(row.high_risk_assets),
            "events_today": int(event_row.events_today),
            "events_last_hour": int(event_row.events_last_hour),
            "open_alerts": int(alert_row.open_alerts),
            "critical_alerts": int(alert_row.critical_alerts),
            "high_alerts": int(alert_row.high_alerts),
            "open_incidents": int(incident_row.open_incidents),
            "critical_incidents": int(incident_row.critical_incidents),
        }

    async def activity(self, start: datetime, end: datetime) -> dict[str, list[dict]]:
        dialect_name = self.session.bind.dialect.name if self.session.bind else "postgresql"
        if dialect_name == "sqlite":
            time_bucket = func.strftime("%Y-%m-%dT%H:00:00+00:00", SecurityEvent.timestamp)
        else:
            time_bucket = func.date_trunc("hour", SecurityEvent.timestamp)

        timeline_rows = (
            await self.session.execute(
                select(time_bucket.label("bucket"), func.count(SecurityEvent.id).label("count"))
                .where(SecurityEvent.timestamp >= start, SecurityEvent.timestamp <= end)
                .group_by(time_bucket)
                .order_by(time_bucket)
            )
        ).all()
        severity_rows = (
            await self.session.execute(
                select(SecurityEvent.severity, func.count(SecurityEvent.id).label("count"))
                .where(SecurityEvent.timestamp >= start, SecurityEvent.timestamp <= end)
                .group_by(SecurityEvent.severity)
                .order_by(func.count(SecurityEvent.id).desc())
            )
        ).all()
        type_rows = (
            await self.session.execute(
                select(SecurityEvent.event_type, func.count(SecurityEvent.id).label("count"))
                .where(SecurityEvent.timestamp >= start, SecurityEvent.timestamp <= end)
                .group_by(SecurityEvent.event_type)
                .order_by(func.count(SecurityEvent.id).desc())
                .limit(8)
            )
        ).all()
        active_asset_rows = (
            await self.session.execute(
                select(
                    SecurityEvent.asset_id,
                    func.coalesce(SecurityEvent.hostname, "Unresolved asset").label("hostname"),
                    func.count(SecurityEvent.id).label("count"),
                )
                .where(SecurityEvent.timestamp >= start, SecurityEvent.timestamp <= end)
                .group_by(SecurityEvent.asset_id, SecurityEvent.hostname)
                .order_by(func.count(SecurityEvent.id).desc())
                .limit(5)
            )
        ).all()

        def bucket_datetime(value: datetime | str) -> datetime:
            if isinstance(value, datetime):
                return value.replace(tzinfo=value.tzinfo or UTC)
            return datetime.fromisoformat(value)

        return {
            "events_over_time": [
                {"timestamp": bucket_datetime(row.bucket), "count": int(row.count)}
                for row in timeline_rows
            ],
            "events_by_severity": [
                {"name": str(row.severity), "count": int(row.count)} for row in severity_rows
            ],
            "events_by_type": [
                {"name": row.event_type, "count": int(row.count)} for row in type_rows
            ],
            "most_active_assets": [
                {
                    "asset_id": row.asset_id,
                    "hostname": row.hostname,
                    "count": int(row.count),
                }
                for row in active_asset_rows
            ],
        }
