from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.lab.assets import CORPORATE_LAB_SOURCES, LAB_HOSTNAMES
from app.models.asset import Asset
from app.models.security_event import SecurityEvent
from app.schemas.lab import LabAssetStatus, LabSourceStatus, LabStatusResponse


class LabStatusService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self) -> LabStatusResponse:
        now = datetime.now(UTC)
        active_after = now - timedelta(seconds=get_settings().lab_telemetry_stale_seconds)
        assets = list(
            await self.session.scalars(
                select(Asset).where(Asset.hostname.in_(LAB_HOSTNAMES)).order_by(Asset.hostname)
            )
        )
        latest_by_asset = {
            asset_id: self._as_utc(timestamp)
            for asset_id, timestamp in (
                await self.session.execute(
                    select(SecurityEvent.asset_id, func.max(SecurityEvent.timestamp))
                    .where(
                        SecurityEvent.asset_id.is_not(None),
                        SecurityEvent.source.in_(CORPORATE_LAB_SOURCES),
                    )
                    .group_by(SecurityEvent.asset_id)
                )
            ).all()
        }
        latest_by_source = {
            source: self._as_utc(timestamp)
            for source, timestamp in (
                await self.session.execute(
                    select(SecurityEvent.source, func.max(SecurityEvent.timestamp))
                    .where(SecurityEvent.source.in_(CORPORATE_LAB_SOURCES))
                    .group_by(SecurityEvent.source)
                )
            ).all()
        }

        asset_statuses = []
        for asset in assets:
            last_telemetry = latest_by_asset.get(asset.id)
            active = last_telemetry is not None and last_telemetry >= active_after
            asset_statuses.append(
                LabAssetStatus(
                    hostname=asset.hostname,
                    display_name=asset.display_name,
                    network_zone=asset.network_zone,
                    status="online" if active else "offline",
                    telemetry_status="active" if active else "stale",
                    last_telemetry=last_telemetry,
                )
            )

        source_statuses = [
            LabSourceStatus(
                source=source,
                status=(
                    "active"
                    if latest_by_source.get(source) is not None
                    and latest_by_source[source] >= active_after
                    else "stale"
                ),
                last_telemetry=latest_by_source.get(source),
            )
            for source in CORPORATE_LAB_SOURCES
        ]
        active_assets = sum(item.status == "online" for item in asset_statuses)
        if active_assets == len(LAB_HOSTNAMES):
            overall = "running"
        elif active_assets:
            overall = "degraded"
        else:
            overall = "offline"
        most_recent = max(latest_by_source.values(), default=None)
        collector_active = most_recent is not None and most_recent >= active_after
        return LabStatusResponse(
            version="0.1",
            status=overall,
            collector_status="active" if collector_active else "stale",
            active_assets=active_assets,
            total_assets=len(LAB_HOSTNAMES),
            assets=asset_statuses,
            sources=source_statuses,
        )

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
