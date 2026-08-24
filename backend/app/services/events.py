from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
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
        asset = None
        if normalized.asset_id:
            asset = await self.asset_repository.get(normalized.asset_id)
            if asset is None:
                raise NotFoundError("ASSET_NOT_FOUND", "Referenced asset does not exist.")
        elif normalized.hostname:
            asset = await self.asset_repository.get_by_hostname(normalized.hostname)

        values = normalized.model_dump()
        if asset:
            values["asset_id"] = asset.id
            values["hostname"] = values["hostname"] or asset.hostname
        event = SecurityEvent(**values)
        await self.repository.create(event)
        await self.session.commit()
        return SecurityEventResponse.model_validate(event)
