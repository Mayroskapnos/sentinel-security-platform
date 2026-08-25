import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.asset import Asset
from app.models.enums import AssetStatus
from app.models.scenario_run import ScenarioRun
from app.models.security_event import SecurityEvent
from app.repositories.assets import AssetRepository
from app.repositories.events import SecurityEventRepository
from app.schemas.common import Page
from app.schemas.security_event import (
    SecurityEventCreate,
    SecurityEventFilters,
    SecurityEventResponse,
)
from app.services.normalization import EventNormalizer

logger = logging.getLogger(__name__)


class SecurityEventService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = SecurityEventRepository(session)
        self.asset_repository = AssetRepository(session)

    async def list(self, filters: SecurityEventFilters) -> Page[SecurityEventResponse]:
        events, total = await self.repository.list(filters)
        return Page[SecurityEventResponse].create(
            items=[SecurityEventResponse.model_validate(event) for event in events],
            page=filters.page,
            page_size=filters.page_size,
            total=total,
        )

    async def get(self, event_id: UUID) -> SecurityEventResponse:
        event = await self.repository.get(event_id)
        if event is None:
            raise NotFoundError("EVENT_NOT_FOUND", "Requested security event does not exist.")
        return SecurityEventResponse.model_validate(event)

    async def create(self, payload: SecurityEventCreate) -> SecurityEventResponse:
        normalized = EventNormalizer.normalize(payload.model_dump())
        await self._validate_scenario_attribution(normalized)
        asset = await self._resolve_asset(normalized)

        values = normalized.model_dump()
        if asset:
            values["asset_id"] = asset.id
            values["hostname"] = values["hostname"] or asset.hostname
            if normalized.timestamp > self._as_utc(asset.last_seen):
                asset.last_seen = normalized.timestamp
            if normalized.normalized_data.get("origin") == "corporate_lab":
                asset.status = AssetStatus.ONLINE

        event = SecurityEvent(**values)
        try:
            await self.repository.create(event)
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
        return SecurityEventResponse.model_validate(event)

    async def _validate_scenario_attribution(self, event: SecurityEventCreate) -> None:
        if event.scenario_run_id is None and event.scenario_id is None:
            return
        run = (
            await self.session.get(ScenarioRun, event.scenario_run_id)
            if event.scenario_run_id
            else None
        )
        if run is not None and run.scenario_id == event.scenario_id:
            normalized_data = dict(event.normalized_data)
            normalized_data["scenario_run_id"] = str(run.id)
            normalized_data["scenario_id"] = run.scenario_id
            event.normalized_data = normalized_data
            return
        logger.warning("event_scenario_attribution_rejected")
        event.scenario_run_id = None
        event.scenario_id = None
        normalized_data = dict(event.normalized_data)
        normalized_data.pop("scenario_run_id", None)
        normalized_data.pop("scenario_id", None)
        normalized_data["scenario_attribution_rejected"] = True
        event.normalized_data = normalized_data

    async def _resolve_asset(self, event: SecurityEventCreate) -> Asset | None:
        asset = None
        if event.asset_id:
            asset = await self.asset_repository.get(event.asset_id)
            if asset is None:
                raise NotFoundError("ASSET_NOT_FOUND", "Referenced asset does not exist.")
            logger.info("event_asset_resolved method=asset_id asset_id=%s", asset.id)
            return asset

        if event.hostname:
            asset = await self.asset_repository.get_by_hostname(event.hostname)
            if asset:
                logger.info("event_asset_resolved method=hostname asset_id=%s", asset.id)
                return asset

        candidate_ips = list(
            dict.fromkeys(ip for ip in (event.destination_ip, event.source_ip) if ip is not None)
        )
        matches = await self.asset_repository.get_by_ip_addresses(candidate_ips)
        if len(matches) == 1:
            logger.info("event_asset_resolved method=ip asset_id=%s", matches[0].id)
            return matches[0]
        if len(matches) > 1:
            logger.warning(
                "event_asset_resolution_ambiguous candidate_count=%d",
                len(matches),
            )
        else:
            logger.info("event_asset_unresolved")
        return None

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
